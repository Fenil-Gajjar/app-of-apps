 mkdir webhook-cdk
cd webhook-cdk

cdk init app --language python

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt


place all the necessary files in this repo to the project and left rest of as it is

then from the root project folder run cdk synth

then run cdk bootstrap aws://account-id/region

then run cdk deploy

after it gets deployed 
edit this kubectl -n argocd edit configmap argocd-notifications-cm

of yaml file
