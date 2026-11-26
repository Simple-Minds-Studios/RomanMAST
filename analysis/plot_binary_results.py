import argparse,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=argparse.ArgumentParser();p.add_argument('report',type=Path);a=p.parse_args()
d=json.loads(a.report.read_text())
names=list(d['single']['instruments'])
fig,axes=plt.subplots(len(names),1,figsize=(12,12),sharex=True)
for ax,k in zip(axes,names):
    for model in ['single','binary']:
        r=d[model]['instruments'][k];t=np.array(r['time']);z=np.array(r['residual']);train=np.array(r['train'])
        ax.scatter(t[train],z[train],s=5,alpha=.3,label=model+' train')
        ax.scatter(t[~train],z[~train],s=12,marker='x',label=model+' held out')
    ax.axhline(0,color='gray');ax.set_ylabel(k);ax.set_xlim(7550,7570);ax.legend(fontsize=7)
axes[-1].set_xlabel('HJD - 2450000');fig.tight_layout()
fig.savefig(a.report.with_suffix('.png'),dpi=180)
