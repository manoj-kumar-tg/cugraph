import torch

from torch_geometric.nn import CuGraphSAGEConv
from torch_geometric.utils.trim_to_layer import TrimToLayer

import torch.nn as nn
import torch.nn.functional as F

class CuGraphSAGE(nn.Module):
    def __init__(self, in_channels, hidden_channels, out_channels, num_layers):
        super().__init__()

        self.convs = torch.nn.ModuleList()
        self.convs.append(CuGraphSAGEConv(in_channels, hidden_channels, aggr='mean'))
        for _ in range(num_layers - 2):
            conv = CuGraphSAGEConv(hidden_channels, hidden_channels, aggr='mean')
            self.convs.append(conv)
        
        self.convs.append(CuGraphSAGEConv(hidden_channels, out_channels, aggr='mean'))

        self._trim = TrimToLayer()

    def forward(self, x, edge, num_sampled_nodes, num_sampled_edges):
        for i, conv in enumerate(self.convs):
            edge = edge.cuda()
            x = x.cuda().to(torch.float32)

            x, edge, _ = self._trim(
                i,
                num_sampled_nodes,
                num_sampled_edges,
                x,
                edge,
                None
            )

            print('max node id:', edge[0].max(), edge[1].max())
            print('x shape:', x.shape[0])

            s = x.shape[0]
            edge_csc = CuGraphSAGEConv.to_csc(edge, (s, s))

            x = conv(x, edge_csc)
            x = F.relu(x)
            x = F.dropout(x, p=0.5)

        x = x.narrow(
            dim=0,
            start=0,
            length=x.shape[0] - num_sampled_nodes[1]
        )

        assert x.shape[0] == num_sampled_nodes[0]
        return x

