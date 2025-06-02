terraform {
    required_providers {
        aws = {
            source  = "hashicorp/aws"
            version = "~> 4.16"
        }
    }

    required_version = ">= 1.2.0"
}

provider "aws" {
    region = var.region
}

data "aws_ami" "ubuntu" {
    most_recent = true
    owners      = ["099720109477"]  # Canonical

    filter {
        name   = "name"
        values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
    }

    filter {
        name   = "virtualization-type"
        values = ["hvm"]
    }

    filter {
        name   = "architecture"
        values = ["x86_64"]
    }
}

resource "aws_key_pair" "aws_key" {
    key_name   = var.aws_key_name
    public_key = file(var.ssh_public_key_path)
}

data "aws_vpc" "default" {
    default = true
}

data "aws_subnets" "default" {
    filter {
        name   = "vpc-id"
        values = [data.aws_vpc.default.id]
    }
}

resource "aws_security_group" "ssh" {
    name        = "allow-ssh"
    description = "Allow SSH"
    vpc_id      = data.aws_vpc.default.id

    ingress {
        description = "SSH from specific IP"
        from_port   = 22
        to_port     = 22
        protocol    = "tcp"
        cidr_blocks = [var.allowed_ssh_cidr]
    }

    egress {
        description = "Allow all outbound traffic"
        from_port   = 0
        to_port     = 0
        protocol    = "-1"
        cidr_blocks = ["0.0.0.0/0"]
    }

    tags = {
        Name = "ale-bench-security-group-ssh"
        Project = "ale-bench"
        ManagedBy = "terraform"
    }
}

resource "aws_instance" "ale_bench_instance" {
    count         = var.instance_count
    ami           = data.aws_ami.ubuntu.id
    instance_type = var.instance_type
    key_name      = aws_key_pair.aws_key.key_name

    vpc_security_group_ids = [aws_security_group.ssh.id]
    subnet_id = tolist(data.aws_subnets.default.ids)[0]
    associate_public_ip_address = true

    root_block_device {
        volume_type           = "gp3"
        volume_size           = var.instance_volume_size
        iops                  = 3000
        throughput            = 125
        delete_on_termination = true
        tags = {
            Name = "ale-bench-instance-${count.index}-storage"
            Project = "ale-bench"
            ManagedBy = "terraform"
        }
    }

    disable_api_stop = false
    disable_api_termination = false
    instance_initiated_shutdown_behavior = "stop"

    user_data = file(var.setup_file_name)

    tags = {
        Name = "ale-bench-instance-${count.index}"
        Project = "ale-bench"
        ManagedBy = "terraform"
    }

    metadata_options {
        http_endpoint = "enabled"
        http_tokens   = "required"
    }

    lifecycle {
        ignore_changes = [ami]
    }
}

output "instance_public_ips" {
    value = sort(aws_instance.ale_bench_instance[*].public_ip)
    description = "Public IP addresses of the instances"
}

output "ssh_connection_string" {
    value = sort([for i in range(var.instance_count) : "ssh -i </path/to/your/secret_key> ubuntu@${aws_instance.ale_bench_instance[i].public_ip}"])
    description = "SSH connection strings for the instances"
}
