import torch
import torch.nn.functional as F

def local_train(model, dataloader, epochs):
    opt = torch.optim.SGD(model.parameters(), lr=0.01)
    model.train()

    for _ in range(epochs):
        for x, y in dataloader:
            opt.zero_grad()
            loss = F.cross_entropy(model(x), y)
            loss.backward()
            opt.step()

    return model
