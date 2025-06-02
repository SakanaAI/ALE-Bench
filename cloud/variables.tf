variable "region" {
    description = "AWS region"
    type        = string
    default     = "us-east-1"
}

variable "instance_type" {
    description = "EC2 instance type"
    type        = string
    default     = "c6i.8xlarge"
}

variable "instance_count" {
    description = "The number of instances to launch"
    type        = number
    default     = 1
}

variable "instance_volume_size" {
    description = "Size of the root volume in GB"
    type        = number
    default     = 100
}

variable "aws_key_name" {
    description = "Name of the AWS key pair"
    type        = string
    default     = "ale-bench"
}

variable "ssh_public_key_path" {
    description = "Path to the public key used for SSH access"
    type        = string
    default     = "~/.ssh/id_rsa.pub"
}

variable "allowed_ssh_cidr" {
    description = "CIDR block allowed for SSH access"
    type        = string
    default     = "0.0.0.0/0"
}

variable "setup_file_name" {
    description = "Name of the setup file to be copied to the instance"
    type        = string
    default     = "setup.sh"
}
