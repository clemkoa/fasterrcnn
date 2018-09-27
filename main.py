import os
import sys
import numpy as np

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

import torchvision.models as models


class RPN(nn.Module):
    def __init__(self):
        super(RPN, self).__init__()

        self.in_dim = 512
        self.anchor_number = 9

        # get the feature map from last conv layer
        resnet = models.resnet101(pretrained=True)
        print(list(resnet.children())[:-2])
        self.feature_map = nn.Sequential(*list(resnet.children())[:-2])
        # define the convrelu layers processing input feature map

        self.RPN_conv = nn.Conv2d(self.in_dim, 512, 3, 1, 1, bias=True)

        # cls layer
        self.cls_layer = nn.Conv2d(512, 2 * self.anchor_number, 1, 1, 0)

        # reg_layer
        self.reg_layer = nn.Conv2d(512, 4 * self.anchor_number, 1, 1, 0)


    def forward(self, x):
       rpn_conv = F.relu(self.RPN_conv(self.feature_map(x)))
       cls = self.cls_layer(rpn_conv)
       reg = self.reg_layer(rpn_conv)


       return 0


rpn = RPN()