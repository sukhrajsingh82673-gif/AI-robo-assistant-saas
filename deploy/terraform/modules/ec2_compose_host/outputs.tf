output "instance_id" {
  description = "The EC2 instance ID"
  value       = aws_instance.app_host.id
}

output "private_ip" {
  description = "The private IP address of the EC2 instance"
  value       = aws_instance.app_host.private_ip
}

output "public_ip" {
  description = "The public IP address (or Elastic IP) of the EC2 instance"
  value       = var.assign_public_ip ? (length(aws_eip.app_eip) > 0 ? aws_eip.app_eip[0].public_ip : aws_instance.app_host.public_ip) : null
}

output "iam_role_arn" {
  description = "The IAM role ARN of the EC2 host"
  value       = aws_iam_role.ec2_role.arn
}
