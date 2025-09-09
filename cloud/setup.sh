#!/usr/bin/bash
set -Eeuo pipefail

# Install docker (https://docs.docker.com/engine/install/ubuntu/)
## Add Docker's official GPG key:
sudo apt-get -qq update
sudo apt-get -qq install -y ca-certificates curl wget
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

## Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get -qq update

## Install the Docker packages.
sudo apt-get -qq install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

## Docker with non-root user
# sudo groupadd docker  # Already created
sudo usermod -aG docker ubuntu
su - ubuntu -c "newgrp docker"


# Install Google Chrome
wget -q -O /tmp/google-chrome-stable_current_amd64.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt-get -qq update
sudo apt-get -qq install -y /tmp/google-chrome-stable_current_amd64.deb
rm /tmp/google-chrome-stable_current_amd64.deb


# Install another dependencies (including the dependencies for the experiments)
sudo apt-get -qq update
sudo apt-get -qq install -y build-essential make unzip libcairo2-dev libffi-dev
sudo apt-get -qq autoremove --purge -y
sudo apt-get -qq clean
rm -rf /var/lib/apt/lists/*


# Install AWS CLI version 2 (https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
su - ubuntu -c "cd /home/ubuntu/ && curl -fsSL https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip -o awscliv2.zip"
su - ubuntu -c "cd /home/ubuntu/ && unzip -qq awscliv2.zip"
su - ubuntu -c "cd /home/ubuntu/ && sudo ./aws/install"
su - ubuntu -c "cd /home/ubuntu/ && rm awscliv2.zip && rm -rf aws"


# Install uv
su - ubuntu -c "curl -fsSL https://astral.sh/uv/install.sh | sh"
su - ubuntu -c "source /home/ubuntu/.local/bin/env"


# Clone the ALE-Bench repository and setup the environment
su - ubuntu -c "cd /home/ubuntu/ && git clone https://github.com/SakanaAI/ALE-Bench.git"
su - ubuntu -c "cd /home/ubuntu/ALE-Bench && uv -q venv --python 3.12.9 && uv -q sync"
su - ubuntu -c "cd /home/ubuntu/ALE-Bench && bash ./scripts/docker_build_all.sh \$(id -u) \$(id -g)"
su - ubuntu -c "docker pull rust:1.79.0-buster"


# Finish
echo "$(printf '\033')[1;4;5;32mALE-Bench setup completed! $(printf '\033')[0m"
