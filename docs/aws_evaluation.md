# Cloud Evaluation with AWS

For standardized benchmarking, we leverage [Terraform by HashiCorp](https://www.terraform.io/) to provision a consistent AWS environment.

Before proceeding, please install the [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) and [Terraform](https://developer.hashicorp.com/terraform/install).

Consult the [Terraform configuration](../cloud/main.tf), [variables file](../cloud/variables.tf), and [setup script](../cloud/setup.sh) for detailed information. We recommend the use of [Amazon EC2 C6i Instances](https://aws.amazon.com/ec2/instance-types/c6i/) for fair evaluations.

**Recommended `num_workers` (parallel evaluations):**
Set `num_workers` to at most the number of **physical cores** of your instance, as most solutions are CPU-bound.

| Instance       | vCPUs | Memory (GiB) | Max `num_workers` | Max `num_workers` (w/ Vis Server) |
|:---------------|:-----:|:------------:|:-----------------:|:---------------------------------:|
| `c6i.xlarge`   | 4     | 8            | 2                 | 1                                 |
| `c6i.2xlarge`  | 8     | 16           | 4                 | 3                                 |
| `c6i.4xlarge`  | 16    | 32           | 8                 | 7                                 |
| `c6i.8xlarge`  | 32    | 64           | 16                | 15                                |
| `c6i.12xlarge` | 48    | 96           | 24                | 23                                |
| `c6i.16xlarge` | 64    | 128          | 32                | 31                                |
| `c6i.24xlarge` | 96    | 192          | 48                | 47                                |
| `c6i.32xlarge` | 128   | 256          | 64                | 63                                |
| `c6i.metal`    | 128   | 256          | 64                | 63                                |


**Workflow:**

1.  **Initialize & Apply Terraform:**
    Before applying, ensure you have an AWS key pair ready. You will need to provide the path to your public key.
    It is also **highly recommended** to restrict SSH access to your IP address for security.
    ```sh
    cd cloud
    terraform init
    terraform apply \
      -var "ssh_public_key_path=</path/to/your/key.pub>" \
      -var "aws_key_name=your-key-pair-name" \
      -var "allowed_ssh_cidr=YOUR_IP_ADDRESS/32" \
      -var "instance_type=c6i.32xlarge" \
      -var "region=us-east-1"
    # Replace </path/to/your/key.pub> with the actual path to your public key.
    # Replace your-key-pair-name with a unique name for the key pair that will be created in AWS.
    # Replace YOUR_IP_ADDRESS/32 with your actual public IP address CIDR (e.g., 123.45.67.89/32).
    # Confirm with 'yes' or use -auto-approve option to skip confirmation
    ```
    The `aws_key_name` variable specifies the name of the key pair to be created in AWS using your provided public key. Ensure the corresponding private key is used for SSH access.

2.  **Connect to the EC2 Instance:**
    ```sh
    ssh -i /path/to/your/key.pem ubuntu@<INSTANCE_PUBLIC_IP>
    ```

3.  **Verify Setup:**
    ```sh
    # Check cloud-init logs for successful completion (This setup takes ~10-20 minutes)
    cat /var/log/cloud-init-output.log
    # Look for "ALE-Bench setup completed!" in green text

    # Confirm ALE-Bench directory and activate virtual environment
    ls /home/ubuntu/ALE-Bench
    source /home/ubuntu/ALE-Bench/.venv/bin/activate
    ```

4.  **Terminate Instance:**
    ```sh
    cd cloud # (Run from your local machine, where the terraform state is located)
    terraform destroy -var "ssh_public_key_path=</path/to/your/key.pub>" -var "region=us-east-1"
    # Confirm with 'yes' or use -auto-approve option to skip confirmation
    ```
