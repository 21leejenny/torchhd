# The following two lines are only needed because of this repository organization
import sys, os

sys.path.insert(1, os.path.realpath(os.path.pardir))

import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision
from torchvision.datasets import MNIST
from tqdm import tqdm

import hdc
import hdc.functional as HDF

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Using {} device".format(device))

DIMENSIONS = 10000
IMG_SIZE = 28
NUM_LEVELS = 1000
BATCH_SIZE = 1  # for GPUs with enough memory we can process multiple images at ones

transform = torchvision.transforms.ToTensor()

train_ds = MNIST("../data", train=True, transform=transform, download=True)
train_ld = torch.utils.data.DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)

test_ds = MNIST("../data", train=False, transform=transform, download=True)
test_ld = torch.utils.data.DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False)


class Model(nn.Module):
    def __init__(self, num_classes, size, train_embedding=False):
        super(Model, self).__init__()

        self.flatten = torch.nn.Flatten()

        self.position = hdc.embeddings.Random(size * size, DIMENSIONS)
        self.position.weight.requires_grad = train_embedding

        self.value = hdc.embeddings.Level(NUM_LEVELS, DIMENSIONS)
        self.value.weight.requires_grad = train_embedding

        self.classify = nn.Linear(DIMENSIONS, num_classes, bias=False)
        self.classify.weight.data.fill_(0.0)

    def encode(self, x):
        x = self.flatten(x)

        sample_hv = HDF.bind(self.position.weight, self.value(x))
        sample_hv = HDF.batch_bundle(sample_hv)

        return HDF.hard_quantize(sample_hv)

    def forward(self, x):
        enc = self.encode(x)
        logit = self.classify(enc)
        return logit


model = Model(len(train_ds.classes), IMG_SIZE)
model = model.to(device)

with torch.no_grad():
    for samples, labels in tqdm(train_ld, desc="Training"):
        samples = samples.to(device)
        labels = labels.to(device)

        samples_hv = model.encode(samples)
        model.classify.weight[labels] += samples_hv

    model.classify.weight[:] = F.normalize(model.classify.weight)


accuracy = hdc.metrics.Accuracy()

with torch.no_grad():
    for samples, labels in tqdm(test_ld, desc="Testing"):
        samples = samples.to(device)

        outputs = model(samples)
        predictions = torch.argmax(outputs, dim=-1)

        accuracy.step(labels, predictions)

print(f"Testing accuracy of {(accuracy.value().item() * 100):.3f}%")