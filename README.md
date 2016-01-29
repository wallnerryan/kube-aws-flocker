
## Installing [Flocker](https://clusterhq.com/flocker/introduction/) on K8S Cluster build with [kube-aws](https://coreos.com/kubernetes/docs/latest/kubernetes-on-aws.html)

### Step 1

[Sign up for an Amazon AWS account](https://portal.aws.amazon.com/gp/aws/developer/registration/index.html)

Install [kube-aws](https://coreos.com/kubernetes/docs/latest/kubernetes-on-aws.html) on your local machine.

### Step 2

Create a `k8s.yaml` for `kube-aws`

Example `k8s.yaml`
```
clusterName: my-k8s-cluster
keyName: ryan
region: us-east-1
availabilityZone: us-east-1c
externalDNSName: my-k8s-master
controllerInstanceType: m3.large
workerCount: 5
workerInstanceType: m3.large
```

Create the Kubernetes Cluster
```
kube-aws --config k8s.yaml up
```

Example Output
```
Waiting for cluster creation...
Successfully created cluster

Cluster Name:	my-k8s-cluster
Controller IP:	52.72.122.10
```

Add your k8s master to your local DNS.
```
$ kube-aws --config k8s.yaml status
Cluster Name: my-k8s-cluster
Controller IP:  52.72.122.10


echo "52.72.122.10  my-k8s-master" | sudo tee -a /etc/hosts
```

Download the `kubtctl` tool to use k8s
```
# (WORKS FOR MAC OSX ONLY)
wget https://storage.googleapis.com/kubernetes-release/release/v1.1.1/bin/darwin/amd64/kubectl
chmod +x kubectl
mv kubectl /usr/local/bin/
```

Use kubctl
```
$:-> kubectl --kubeconfig=clusters/my-k8s-cluster/kubeconfig  get no
NAME                         LABELS                                              STATUS    AGE
ip-10-0-0-231.ec2.internal   kubernetes.io/hostname=ip-10-0-0-231.ec2.internal   Ready     26m
ip-10-0-0-232.ec2.internal   kubernetes.io/hostname=ip-10-0-0-232.ec2.internal   Ready     26m
ip-10-0-0-233.ec2.internal   kubernetes.io/hostname=ip-10-0-0-233.ec2.internal   Ready     21m
ip-10-0-0-234.ec2.internal   kubernetes.io/hostname=ip-10-0-0-234.ec2.internal   Ready     26m
ip-10-0-0-235.ec2.internal   kubernetes.io/hostname=ip-10-0-0-235.ec2.internal   Ready     26m
```

### Step 3

Find the security group ids for the `Controller` and `Worker` nodes. You can find then with `aws ec2` or in your AWS Console.

Examples
```
my-k8s-cluster-SecurityGroupController-V8UYEYRURKJB --> id: sg-e68fdd9f
my-k8s-cluster-SecurityGroupWorker-1EGC2JQ7O4ZAD --> id: sg-e48fdd9d
```

Open up flocker ports, and app ports (Redis)
```
(Flocker)
aws ec2 authorize-security-group-ingress --group-id sg-e68fdd9f --protocol tcp --port 4523-4524 --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress --group-id sg-e48fdd9d --protocol tcp --port 4523-4524 --cidr 0.0.0.0/0
```

### Step 4

Install UFT installer and create a yaml file to install Flocker and Install Flocker

You can find how to [get started with UFT Installer here](https://docs.clusterhq.com/en/1.9.0/labs/installer-getstarted.html)

Create a `flocker.yaml`

Example Flocker YAML. 

> **Replace the public IPs, Private IPs, key location and Control Node. The control node DNS is your K8S Master DNS.

```
cluster_name: my-cluster
agent_nodes:
 - {public: 52.90.51.238, private: 10.0.0.106}
 - {public: 54.86.30.102, private: 10.0.0.108}
 - {public: 54.208.136.26, private: 10.0.0.105}
 - {public: 54.175.245.134, private: 10.0.0.27}
 - {public: 52.90.57.92, private: 10.0.0.144}

control_node: ec2-52-72-122-10.compute-1.amazonaws.com
users:
 - coreuser
os: coreos
private_key_path: /Users/wallnerryan/ryan.pem
agent_config:
  version: 1
  control-service:
     hostname: ec2-52-72-122-10.compute-1.amazonaws.com
     port: 4524
  dataset:
    backend: "aws"
    region: "us-east-1"
    zone: "us-east-1c"
    access_key_id: "<Your AWS Key>"
    secret_access_key: "<Your AWS Secre Key>"
```

Hint: You can find the IPs easily with AWS CLI
```
(Public)
aws ec2 describe-instances --filters Name=instance.group-id,Values=sg-e48fdd9d | grep PublicIpAddress | sed 's/\"//g' | sed 's/\,//g' |  tr -d " " | awk -F: '{print $2}'

(Private)
aws ec2 describe-instances --filters Name=instance.group-id,Values=sg-e48fdd9d | grep PrivateIpAddress | sed 's/\"//g' | sed 's/\,//g' |  tr -d " " | uniq -d | awk -F: '{print $2}'
```

Install Flocker
```
uft-flocker-install flocker.yml
uft-flocker-config flocker.yml
```

> `uft-flocker-config` might take a while as it needs to download containers

### Configure your Flocker + K8S Cluster to use Flocker and a Backend.

Run the configuration script
```
cd /your/uft/cluster/dir
./path/to/this/repo/dir/config_k8s_flocker.py flocker.yml
```

Set up flocker CTL
```
$:-> cp coreuser.crt user.crt
$:-> cp coreuser.key user.key
$:-> flockerctl --control-service=ec2-52-72-148-79.compute-1.amazonaws.com list-nodes
SERVER     ADDRESS
ffb06567   10.0.0.105
211adc21   10.0.0.103
0817d122   10.0.0.102
72022b31   10.0.0.101
0ec16ccc   10.0.0.104
```
