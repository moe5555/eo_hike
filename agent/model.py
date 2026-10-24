"""The agent's self-grown perception: a small conv autoencoder, random init from the seed.

32x32x3 in [0, 1] -> 4 stride-2 convs (32->16->8->4->2) -> linear -> 64-d latent -> mirror.
~270k parameters. No normalisation layers, so the progress probe can vmap over clones.
"""

from __future__ import annotations

import torch
from torch import nn

CH = (16, 32, 64, 96)
LATENT = 64


class ConvAE(nn.Module):
    def __init__(self, ch: tuple[int, ...] = CH, latent: int = LATENT) -> None:
        super().__init__()
        enc, c_in = [], 3
        for c in ch:
            enc += [nn.Conv2d(c_in, c, 3, stride=2, padding=1), nn.LeakyReLU(0.2)]
            c_in = c
        self.enc = nn.Sequential(*enc)
        self.to_z = nn.Linear(ch[-1] * 4, latent)
        self.from_z = nn.Linear(latent, ch[-1] * 4)
        dec, rev = [], list(ch[::-1]) + [ch[0]]
        for a, b in zip(rev[:-1], rev[1:]):
            dec += [nn.ConvTranspose2d(a, b, 4, stride=2, padding=1), nn.LeakyReLU(0.2)]
        dec += [nn.Conv2d(ch[0], 3, 3, padding=1), nn.Sigmoid()]
        self.dec = nn.Sequential(*dec)
        self.ch = ch

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        return self.to_z(self.enc(x).flatten(1))

    def decode(self, z: torch.Tensor) -> torch.Tensor:
        return self.dec(self.from_z(z).view(-1, self.ch[-1], 2, 2))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.decode(self.encode(x))


if __name__ == "__main__":
    m = ConvAE()
    print(sum(p.numel() for p in m.parameters()), m(torch.rand(2, 3, 32, 32)).shape)
