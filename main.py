import argparse
import os
import sys
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from dataset import ToothImageDataset
from src.rpn import RPN
from src.fasterrcnn import FasterRCNN

model = 'resnet50'
MODEL_PATH = os.path.join('models', f'fasterrcnn_{model}.pt')

def train_fasterrcnn(dataset):
    save_range = 10
    lamb = 10.0

    fasterrcnn = FasterRCNN(len(dataset.get_classes()), model=model, path=MODEL_PATH)
    optimizer = optim.SGD(fasterrcnn.parameters(), lr = 0.1)

    for i in range(1, len(dataset)):
        optimizer.zero_grad()
        im, bboxes, classes = dataset[i]
        all_cls, all_reg, proposals, rpn_cls, rpn_reg = fasterrcnn(torch.from_numpy(im).float())
        # print(keep)
        # print(all_reg.shape)
        # print(all_cls.shape)

        rpn_reg_target, rpn_cls_target, rpn_selected_indices, rpn_positives = fasterrcnn.rpn.get_target(bboxes)
        cls_target, reg_target = fasterrcnn.get_target(proposals, bboxes, classes)

        rpn_reg_loss = F.smooth_l1_loss(rpn_reg[rpn_positives], rpn_reg_target[rpn_positives])
        # look at a sample of positive + negative boxes for classification
        rpn_cls_loss = F.binary_cross_entropy(rpn_cls[rpn_selected_indices], rpn_cls_target[rpn_selected_indices].float())

        fastrcnn_reg_loss = F.smooth_l1_loss(all_reg, reg_target)
        fastrcnn_cls_loss = F.binary_cross_entropy(all_cls, cls_target)

        rpn_loss = rpn_cls_loss + lamb * rpn_reg_loss
        fastrcnn_loss = fastrcnn_cls_loss + lamb * fastrcnn_reg_loss
        print(rpn_loss, fastrcnn_loss)

        loss = rpn_loss + fastrcnn_loss

        loss.backward()
        optimizer.step()

        print('[%d] loss: %.5f' % (i, loss.item()))

        if i % save_range == 0:
            torch.save(fasterrcnn.state_dict(), MODEL_PATH)
    print('Finished Training')

def train(dataset):
    save_range = 10
    lamb = 10.0

    rpn = RPN(model=model, path=MODEL_PATH)
    optimizer = optim.SGD(rpn.parameters(), lr = 0.1)

    for i in range(1, len(dataset)):
        optimizer.zero_grad()
        im, bboxes, classes = dataset[i]
        reg_truth, cls_truth, selected_indices, positives = rpn.get_target(bboxes)

        cls_output, reg_output = rpn(torch.from_numpy(im).float())
        # only look at positive boxes for regression loss
        reg_loss = F.smooth_l1_loss(reg_output[positives], reg_truth[positives])
        # look at a sample of positive + negative boxes for classification
        cls_loss = F.binary_cross_entropy(cls_output[selected_indices], cls_truth[selected_indices].float())

        loss = cls_loss + lamb * reg_loss
        if not len(positives):
            loss = cls_loss

        loss.backward()
        optimizer.step()

        print('[%d] loss: %.5f' % (i, loss.item()))

        if i % save_range == 0:
            torch.save(rpn.state_dict(), MODEL_PATH)
    print('Finished Training')

def infer(dataset):
    with torch.no_grad():
        rpn = RPN(model=model, path=MODEL_PATH)

        # TODO change hardcoded range for test dataset
        for i in range(1, len(dataset)):
            im, bboxes, classes = dataset[i]
            cls, reg = rpn(torch.from_numpy(im).float())
            bboxes = rpn.get_proposals(reg, cls)

            dataset.visualise_proposals_on_image(bboxes, i)

def main(args):
    dataset = ToothImageDataset('data')
    if args.infer:
        infer(dataset)
    if args.train:
        train(dataset)
    if args.test:
        train_fasterrcnn(dataset)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--train', action='store_true')
    parser.add_argument('-i', '--infer', action='store_true')
    parser.add_argument('-test', '--test', action='store_true')
    args = parser.parse_args()

    main(args)
