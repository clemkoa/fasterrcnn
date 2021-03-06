import argparse
import os
import sys
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from dataset import VOCDataset
from src.rpn import RPN
from src.fasterrcnn import FasterRCNN

model = 'resnet50'
MODEL_PATH = os.path.join('models', f'fasterrcnn_{model}.pt')

def train(dataset):
    save_range = 40
    lamb = 10.0
    n_classes = len(dataset.get_classes())

    fasterrcnn = FasterRCNN(n_classes, model=model, path=MODEL_PATH, training=True)
    optimizer = optim.Adam(fasterrcnn.parameters(), lr = 0.0001)

    for i in range(1, len(dataset)):
        im, bboxes, classes = dataset[i]
        if not len(classes):
            continue
        print(i)
        optimizer.zero_grad()
        all_cls, all_reg, proposals, rpn_cls, rpn_reg = fasterrcnn(torch.from_numpy(im).float())

        rpn_reg_target, rpn_cls_target, rpn_selected_indices, rpn_positives = fasterrcnn.rpn.get_target(bboxes)
        cls_target, reg_target = fasterrcnn.get_target(proposals, bboxes, classes)
        print(cls_target)

        rpn_reg_loss = F.smooth_l1_loss(rpn_reg[rpn_positives], rpn_reg_target[rpn_positives])
        # look at a sample of positive + negative boxes for classification
        rpn_cls_loss = F.binary_cross_entropy(rpn_cls[rpn_selected_indices], rpn_cls_target[rpn_selected_indices].float())

        fastrcnn_reg_loss = F.smooth_l1_loss(all_reg, reg_target)
        fastrcnn_cls_loss = F.cross_entropy(all_cls, cls_target)
        rpn_loss = rpn_cls_loss + lamb * rpn_reg_loss

        fastrcnn_loss = fastrcnn_cls_loss + fastrcnn_reg_loss
        print(rpn_reg_loss, rpn_cls_loss, fastrcnn_reg_loss, fastrcnn_cls_loss)
        loss = rpn_loss + fastrcnn_loss

        loss.backward()
        optimizer.step()

        print('[%d] loss: %.5f'.format(i, loss.item()))

        if i % save_range == 0:
            torch.save(fasterrcnn.state_dict(), MODEL_PATH)
    print('Finished Training')


def test(dataset):
    save_range = 40
    lamb = 10.0
    n_classes = len(dataset.get_classes())

    fasterrcnn = FasterRCNN(n_classes, model=model, path=MODEL_PATH, training=True)

    for i in range(1, len(dataset)):
        im, bboxes, classes = dataset[i]
        # dataset.visualise_proposals_on_image(bboxes, i)
        print(classes)
        if not len(classes):
            continue
        anchors = fasterrcnn.rpn.get_positive_anchors(bboxes)
        dataset.visualise_proposals_on_image(anchors, i)

def infer(dataset):
    with torch.no_grad():
        n_classes = len(dataset.get_classes())
        fasterrcnn = FasterRCNN(n_classes, model=model, path=MODEL_PATH)

        # TODO change hardcoded range for test dataset
        for i in range(1, len(dataset)):
            im, bboxes, classes = dataset[i]
            cls, reg, rpn_proposals, rpn_cls, rpn_reg = fasterrcnn(torch.from_numpy(im).float())
            print(cls)
            bboxes = fasterrcnn.get_proposals(reg, cls, rpn_proposals)

            dataset.visualise_proposals_on_image(bboxes, i)

def main(args):
    dataset = VOCDataset('data')
    # return test(dataset)
    if args.infer:
        infer(dataset)
    if args.train:
        train(dataset)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--train', action='store_true')
    parser.add_argument('--name', nargs=1, default='index', type=str)
    parser.add_argument('-i', '--infer', action='store_true')
    parser.add_argument('-test', '--test', action='store_true')
    args = parser.parse_args()

    main(args)
