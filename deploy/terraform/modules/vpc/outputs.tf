output "vpc_id" {
  description = "The ID of the VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

output "private_app_subnet_ids" {
  description = "IDs of the private application subnets"
  value       = aws_subnet.private_app[*].id
}

output "private_db_subnet_ids" {
  description = "IDs of the private database subnets"
  value       = aws_subnet.private_db[*].id
}

output "ingress_security_group_id" {
  description = "ID of the Ingress Security Group"
  value       = aws_security_group.ingress_sg.id
}

output "app_host_security_group_id" {
  description = "ID of the Application Host Security Group"
  value       = aws_security_group.app_host_sg.id
}

output "db_security_group_id" {
  description = "ID of the Database Security Group"
  value       = aws_security_group.db_sg.id
}
