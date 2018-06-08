import torchvision.models.resnet as m
import torch.nn as nn
import torch.nn.functional as F

import waterboy.modules.layers as l
from waterboy.api.base import Model


# Because of concat pooling it's 2x 512
NET_OUTPUT = 1024


class Resnet34(Model):
    def __init__(self, fc_layers=None, dropout=None, pretrained=True):
        super().__init__()

        # Store settings, maybe someone will be interested to see them
        self.fc_layers = fc_layers
        self.dropout = dropout
        self.pretrained = pretrained
        self.head_layers = 8

        # Load backbbone
        backbone = m.resnet34(pretrained=pretrained)

        # If fc layers is set, let's put custom head
        if fc_layers:
            # Take out the old head and let's put the new head
            valid_children = list(backbone.children())[:-2]

            valid_children.extend([
                l.AdaptiveConcatPool2d(),
                l.Flatten()
            ])

            layer_inputs = [NET_OUTPUT] + fc_layers[:-1]

            dropout = dropout or [None] * len(fc_layers)

            for idx, (layer_input, layet_output, layer_dropout) in enumerate(zip(layer_inputs, fc_layers, dropout)):
                valid_children.append(nn.BatchNorm1d(layer_input))

                if layer_dropout:
                    valid_children.append(nn.Dropout(layer_dropout))

                valid_children.append(nn.Linear(layer_input, layet_output))

                if idx == len(fc_layers) - 1:
                    # Last layer
                    valid_children.append(nn.LogSoftmax(dim=1))
                else:
                    valid_children.append(nn.ReLU())

            final_model = nn.Sequential(*valid_children)
        else:
            final_model = backbone

        self.model = final_model

    def freeze(self, number=None):
        """ Freeze given number of layers in the model """
        if number is None:
            number = self.head_layers

        for idx, child in enumerate(self.model.children()):
            if idx < number:
                for parameter in child.parameters():
                    parameter.requires_grad = False

    def forward(self, x):
        return self.model(x)

    def loss_value(self, x_data, y_true, y_pred):
        """ Calculate value of the loss function """
        return F.nll_loss(y_pred, y_true)

    def metrics(self):
        """ Set of metrics for this model """
        from waterboy.metrics.loss_metric import Loss
        from waterboy.metrics.accuracy import Accuracy
        return [Loss(), Accuracy()]


def create(fc_layers=None, dropout=None, pretrained=True):
    """ Create a Resnet-34 model with a custom head """
    return Resnet34(fc_layers, dropout, pretrained)