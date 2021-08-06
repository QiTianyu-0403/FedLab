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

import torch
import json

class AverageMeter(object):
    """Record train infomation"""

    def __init__(self):
        self.reset()

    def reset(self):
        self.val = 0.0
        self.avg = 0.0
        self.sum = 0.0
        self.count = 0.

    def update(self, val, n=1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count


def evaluate(model, criterion, test_loader, cuda):
    """
    Evaluate local model based on given test :class:`torch.DataLoader`
    Args:
        test_loader (torch.DataLoader): :class:`DataLoader` for evaluation
        cuda (bool): Use GPUs or not
    """
    model.eval()
    loss_sum = 0.0
    correct = 0.0
    total = 0.0
    with torch.no_grad():
        for inputs, labels in test_loader:
            if cuda:
                inputs = inputs.cuda()
                labels = labels.cuda()

            outputs = model(inputs)
            loss = criterion(outputs, labels)

            _, predicted = torch.max(outputs, 1)
            correct += torch.sum(predicted.eq(labels)).item()
            total += len(labels)
            loss_sum += loss.item()

    accuracy = correct / total
    # TODO: is it proper to use loss_sum here?? CrossEntropyLoss is averaged over each sample
    log_str = "Evaluate, Loss {}, accuracy: {}".format(loss_sum,
                                                       accuracy)
    print(log_str)
    return loss_sum, accuracy


def read_config_from_json(json_file: str, user_name: str):
    """Read config from `json_file` to get config for `user_name`

    Args:
        json_file (str): path for json_file
        user_name (str): read config for this user, it can be 'server' or 'client_id'

    Returns:
        a tuple with ip, port, world_size, rank about user with `user_name`

    Examples:
        read_config_from_json('../../../tests/data/config.json', 'server')

    Notes:
        config.json example as follows
        {
          "server": {
            "ip" : "127.0.0.1",
            "port": "3002",
            "world_size": 3,
            "rank": 0
          },
          "client_0": {
            "ip": "127.0.0.1",
            "port": "3002",
            "world_size": 3,
            "rank": 1
          },
          "client_1": {
            "ip": "127.0.0.1",
            "port": "3002",
            "world_size": 3,
            "rank": 2
          }
        }
    """
    with open(json_file) as f:
        config = json.load(f)
    config_info = config[user_name]
    return config_info['ip'], config_info['port'], config_info['world_size'], config_info['rank']
