# Copyright 2021 Peng Cheng Laboratory (http://www.szpclab.com/) and FedLab Authors (smilelab.group)

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

from fedlab_core.network_manager import NetworkManager
from fedlab_utils.message_code import MessageCode
from fedlab_utils.serialization import SerializationTool
from fedlab_core.communicator.processor import Package, PackageProcessor
from fedlab_core.network import DistNetwork
from fedlab_utils.logger import logger


class ClientPassiveManager(NetworkManager):
    """Passive communication Manager

    Args:
        handler (`ClientBackendHandler`): Subclass of ClientBackendHandler. Provides meth:train and attribute:model.
        network (`DistNetwork`): distributed network initialization.
        logger (`logger`, optional): object of `fedlab_utils.logger`
    """

    def __init__(self, handler, network: DistNetwork, logger=None):
        super(ClientPassiveManager, self).__init__(network, handler)

        if logger is None:
            logging.getLogger().setLevel(logging.INFO)
            self._LOGGER = logging
        else:
            self._LOGGER = logger

    def run(self):
        """Main procedure of each client is defined here:
            1. client waits for data from server （PASSIVE）
            2. after receiving data, client will train local model
            3. client will synchronize with server actively
        """
        self._LOGGER.info("connecting with server")
        self._network.init_network_connection()
        while True:
            self._LOGGER.info("Waiting for server...")
            # waits for data from
            sender_rank, message_code, payload = PackageProcessor.recv_package(
                src=0)
            # exit
            if message_code == MessageCode.Exit:
                self._LOGGER.info(
                    "Recv {}, Process exiting".format(message_code))
                exit(0)
            else:
                # perform local training
                self.on_receive(sender_rank, message_code, payload)

            # synchronize with server
            self.synchronize()

    def on_receive(self, sender_rank, message_code, payload):
        """Actions to perform on receiving new message, including local training

        Args:
            sender_rank (int): Rank of sender
            message_code (MessageCode): Agreements code defined in: class:`MessageCode`
            payload (torch.Tensor): Serialized parameters
        """
        self._LOGGER.info("Package received from {}, message code {}".format(
            sender_rank, message_code))
        s_parameters = payload[0]
        self._handler.train(model_parameters=s_parameters)

    def synchronize(self):
        """Synchronize local model with server actively"""
        self._LOGGER.info("synchronize model parameters with server")
        model_params = SerializationTool.serialize_model(self._handler.model)
        pack = Package(message_code=MessageCode.ParameterUpdate,
                       content=model_params)
        PackageProcessor.send_package(pack, dst=0)


class ClientActiveManager(NetworkManager):
    """Active communication Manager

        Args:
            handler: Subclass of ClientBackendHandler, manages training and evaluation of local model on each client.
            network (`DistNetwork`): distributed network initialization.
            local_epochs (int): epochs for local train
            logger (`logger`, optional): object of `fedlab_utils.logger`
    """

    def __init__(self,
                 handler,
                 network: DistNetwork,
                 local_epochs: int = None,
                 logger: logger = None):
        super(ClientActiveManager, self).__init__(network, handler)

        # temp variables, can assign train epoch rather than initial epoch value in handler
        self.epochs = local_epochs
        self.model_gen_time = None  # record received model's generated update time

        if logger is None:
            logging.getLogger().setLevel(logging.INFO)
            self._LOGGER = logging
        else:
            self._LOGGER = logger

    def run(self):
        """Main procedure of each client is defined here:
            1. client requests data from server (ACTIVE)
            2. after receiving data, client will train local model
            3. client will synchronize with server actively
        """
        self._LOGGER.info("connecting with server")
        self._network.init_network_connection()
        while True:
            self._LOGGER.info("Waiting for server...")
            # request model actively
            self.request_model()
            # waits for data from
            sender_rank, message_code, payload = PackageProcessor.recv_package(
                src=0)

            # exit
            if message_code == MessageCode.Exit:
                self._LOGGER.info(
                    "Recv {}, Process exiting".format(message_code))
                exit(0)

            # perform local training
            self.on_receive(sender_rank, message_code, payload)

            # synchronize with server
            self.synchronize()

    def on_receive(self, sender_rank, message_code, payload):
        """Actions to perform on receiving new message, including local training

        Args:
            sender_rank (int): Rank of sender
            message_code (MessageCode): Agreements code defined in: class:`MessageCode`
            s_parameters (torch.Tensor): Serialized model parameters
        """
        self._LOGGER.info("Package received from {}, message code {}".format(
            sender_rank, message_code))
        s_parameters = payload[0]
        self.model_gen_time = payload[1]
        # move loading model params to the start of training
        self._handler.train(epoch=self.epochs, model_parameters=s_parameters)

    def synchronize(self):
        """Synchronize local model with server actively"""
        self._LOGGER.info("synchronize model parameters with server")
        model_params = SerializationTool.serialize_model(self._handler.model)
        pack = Package(message_code=MessageCode.ParameterUpdate)
        pack.append_tensor_list([model_params, self.model_gen_time])
        PackageProcessor.send_package(pack, dst=0)

    def request_model(self):
        """send ParameterRequest"""
        self._LOGGER.info("request model parameters from server")
        pack = Package(message_code=MessageCode.ParameterRequest)
        PackageProcessor.send_package(pack, dst=0)