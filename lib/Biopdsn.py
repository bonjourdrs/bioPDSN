from lib.models.resnet import Resnet
from facenet_pytorch import MTCNN
from lib.data.rmfd_dataset import MaskDataset

import pytorch_lightning as pl
from sklearn.model_selection import train_test_split
import pandas as pd

import torch
import torch.nn as nn
from torch.optim import Adam
from torch.optim.optimizer import Optimizer
from torch.utils.data import DataLoader
'''
args example
args = {
    "batch_size" : 1,
    "input_size" : '3,112,112',
    "model_path" : "./weights/model-r50-am-lfw/model,00",
    "mtcnn_norm": True,
    "keep_all": False,
    "dfPath": 'data/merged_df.pickle'
} 
'''

class BioPDSN(pl.LightningModule):
    def __init__(self,args):
        super(BioPDSN,self).__init__()
        self.batch_size = args.batch_size
        self.num_workers = args.num_workers
        self.dfPath = args.dfPath
        self.df = None
        self.trainDF = None
        self.validateDF = None
        #self.crossEntropyLoss = None
        self.lr = 0.02
        self.momentum = args.momentum
        self.weight_decay = args.weight_decay
        
        self.imageShape = [int(x) for x in args.input_size.split(',')]
        self.features_shape = 512
        #self.device = torch.device('cuda:0') if torch.cuda.is_available() else torch.device('cpu')
        self.mtcnn = MTCNN(image_size=self.imageShape[1], min_face_size=80, 
                            device = self.device, post_process=args.mtcnn_norm,
                            keep_all=args.keep_all)
        self.resnet = Resnet(args)
        self.loss_diff = nn.L1Loss(reduction='mean').to(self.device) 
        self.loss_cls = nn.CrossEntropyLoss().to(self.device)

        # Mask Generator
        self.sia = nn.Sequential(
            #nn.BatchNorm2d(filter_list[4]),
            nn.Conv2d(self.features_shape, 512, kernel_size=3, stride=1, padding=1, bias=False),
            nn.PReLU(self.features_shape),
            nn.BatchNorm2d(self.features_shape),
            nn.Sigmoid(),
        )
        self.fc = nn.Sequential(
            nn.BatchNorm1d(self.features_shape * 7 * 6),
            #nn.Dropout(p=0),
            nn.Linear(self.features_shape * 7 * 6, 512),
            nn.BatchNorm1d(512),
        )
        # Weight initialization
        for m in self.modules():
            if (isinstance(m, nn.Conv2d) or isinstance(m, nn.Linear)):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.constant(m.bias, 0.0)
            elif (isinstance(m, nn.BatchNorm2d) or isinstance(m, nn.BatchNorm1d)):
                nn.init.constant_(m.weight,1)
                nn.init.constant_(m.bias,0)
        
        freeze_layers()
        
    def freeze_layers(self):
        for name, param in self.named_parameters():
            if 'mtcnn' in name:
                param.requires_grad = False
        
    def get_faces(self,batch):
        if (type(batch) == list):
            batch = [img.resize(self.imageShape[1]) for img in batch]
        return self.mtcnn(batch)

    
    def get_features(self,source,target):
        batch = [source,target]
        faces = self.get_faces(batch)
        features = self.resnet.get_features(faces) #type(features) = numpy ndarray

        return features

    def forward(self,source,target):
        f1,f2 = self.get_features(source,target)

        # Begin Siamese branch
        f_diff = torch.add(f1, -1.0, f2)
        f_diff = torch.abs(f_diff)
        out = self.sia(f_diff)
        # End Siamese branch

        f1_masked = f1 * out
        f2_masked = f2 * out

        fc1 = f1_masked.view(f1_masked.size(0), -1) #256*(512*7*6)
        fc2 = f2_masked.view(f2_masked.size(0), -1)
        fc1 = self.fc(fc1)
        fc2 = self.fc(fc2)

        return f1_masked, f2_masked, fc1, fc2, f_diff, out

    def prepare_data(self):
        self.df = pd.read_pickle(self.dfPath)
        train, validate = train_test_split(df, test_size=0.2, random_state=42,stratify=self.df.id_class)
        self.trainDF = MaskDataset(train,self.imageShape[-2:])
        self.validateDF = MaskDataset(validate,self.imageShape[-2:])

    def train_dataloader(self):
        return DataLoader(self.trainDF, batch_size=self.batch_size, shuffle=True, num_workers=self.num_workers)
    
    def val_dataloader(self):
        return DataLoader(self.validateDF, batch_size=self.batch_size, num_workers=self.num_workers)
    
    def configure_optimizers(self):
        optimizer = torch.optim.SGD(filter(lambda p: p.requires_grad, self.parameters()),
                                lr=self.lr,
                                momentum=self.momentum,
                                weight_decay=self.weight_decay)
    
        return optimizer


