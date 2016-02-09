#!/usr/bin/env python

import sys, os
import csv
import subprocess

# Usage: run_tests.py cluster.yml
from utils import Configurator, verify_socket, log
from twisted.internet.task import react
from twisted.internet.defer import gatherResults, inlineCallbacks
from twisted.python.filepath import FilePath

def report_completion(result, public_ip, message="Completed"):
    log(message, public_ip)
    return result

class UsageError(Exception):
    pass

@inlineCallbacks
def main(reactor, configFile):
    c = Configurator(configFile=configFile)

    if c.config["os"] == "ubuntu":
        user = "ubuntu"
    elif c.config["os"] == "centos":
        user = "centos"
    elif c.config["os"] == "amazon":
        user = "ec2-user"

    # Gather IPs of all nodes
    nodes = c.config["agent_nodes"]
    node_public_ips = [n["public"] for n in nodes]
    node_public_ips.append(c.config["control_node"])

    # Wait for all nodes to boot
    yield gatherResults([verify_socket(ip, 22, timeout=600) for ip in node_public_ips])

    log("Generating API certs")
    # generate and upload plugin.crt and plugin.key for each node
    for public_ip in node_public_ips:
        # use the node IP to name the local files
        # so they do not overwrite each other
        c.run("flocker-ca create-api-certificate %s-plugin" % (public_ip,))
        log("Generated api certs for", public_ip)

    deferreds = []
    log("Uploading api certs...")
    for public_ip in node_public_ips:
        # upload the .crt and .key
        for ext in ("crt", "key"):
            d = c.scp("%s-plugin.%s" % (public_ip, ext,),
                public_ip, "/etc/flocker/api.%s" % (ext,), async=True)
            d.addCallback(report_completion, public_ip=public_ip, message=" * Uploaded api cert for")
            deferreds.append(d)
    yield gatherResults(deferreds)
    log("Uploaded api certs")

    deferreds = []
    if user == "ubuntu":
        for public_ip in node_public_ips:
            cmd = """echo 
cat >> /etc/sysconfig/kubelet << EOF
FLOCKER_CONTROL_SERVICE_HOST=%s\n
FLOCKER_CONTROL_SERVICE_PORT=4523\n
FLOCKER_CONTROL_SERVICE_CA_FILE=/etc/flocker/cluster.crt\n
FLOCKER_CONTROL_SERVICE_CLIENT_KEY_FILE=/etc/flocker/api.key\n
FLOCKER_CONTROL_SERVICE_CLIENT_CERT_FILE=/etc/flocker/api.crt
EOF""" % c.config['control_node']
            d = c.runSSHAsync(public_ip, cmd)
            d.addCallback(report_completion, public_ip=public_ip, message="Enabled flocker ENVs for")
            deferreds.append(d)
    else:
        for public_ip in node_public_ips:
            cmd = """echo 
cat > /etc/flocker/env << EOF
FLOCKER_CONTROL_SERVICE_HOST=%s\n
FLOCKER_CONTROL_SERVICE_PORT=4523\n
FLOCKER_CONTROL_SERVICE_CA_FILE=/etc/flocker/cluster.crt\n
FLOCKER_CONTROL_SERVICE_CLIENT_KEY_FILE=/etc/flocker/api.key\n
FLOCKER_CONTROL_SERVICE_CLIENT_CERT_FILE=/etc/flocker/api.crt
EOF""" % c.config['control_node']
            d = c.runSSHAsync(public_ip, cmd)
            d.addCallback(report_completion, public_ip=public_ip, message="Enabled flocker ENVs for")
            deferreds.append(d)
    yield gatherResults(deferreds)
    log("Uploaded Flocker ENV file.")

    deferreds = []
    if user == "ubuntu":
        # Do nothing, we dont place an ENV.
        pass
    else:
        for public_ip in node_public_ips:
            cmd = """echo
sed -i -e 's,/usr/bin/kubelet,/root/kubelet,g' /etc/systemd/system/kubelet.service;
sed  -i '/\[Service\]/aEnvironmentFile=/etc/flocker/env' /etc/systemd/system/kubelet.service
"""
            d = c.runSSHAsync(public_ip, cmd)
            d.addCallback(report_completion, public_ip=public_ip, message="Configured flocker ENVs for")
            deferreds.append(d)
    yield gatherResults(deferreds)
    log("Configured Flocker ENV file.")

    deferreds = []
    if user == "ubuntu":
        cmd = """echo
systemctl restart kubelet;
"""
            d = c.runSSHAsync(public_ip, cmd)
            d.addCallback(report_completion, public_ip=public_ip, message="Restarted Kubelet for")
            deferreds.append(d)
    else:
        for public_ip in node_public_ips:
            cmd = """echo
wget https://storage.googleapis.com/kubernetes-release/release/v1.1.1/bin/linux/amd64/kubelet;
 chmod +x kubelet;
 systemctl daemon-reload;
 systemctl restart kubelet;
"""
            d = c.runSSHAsync(public_ip, cmd)
            d.addCallback(report_completion, public_ip=public_ip, message="Restarted Kubelet for")
            deferreds.append(d)
    yield gatherResults(deferreds)
    log("Restarted Kubelet")

    log("Completed")

def _main():
    react(main, sys.argv[1:])

if __name__ == "__main__":
    _main()
