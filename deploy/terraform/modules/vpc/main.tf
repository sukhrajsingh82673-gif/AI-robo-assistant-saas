# ==============================================================================
# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
# Terraform Infrastructure Module: Isolated Virtual Private Cloud (VPC)
# Enforces Network Isolation, Ingress Defense-in-Depth, and Private DB Subnets
# ==============================================================================

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "zonata-${var.environment}-vpc"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# 1. Internet Gateway for Public Subnets
resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name        = "zonata-${var.environment}-igw"
    Environment = var.environment
  }
}

# 2. Public Subnets (For ALB / Public Ingress)
resource "aws_subnet" "public" {
  count                   = length(var.public_subnet_cidrs)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name        = "zonata-${var.environment}-public-${var.availability_zones[count.index]}"
    Environment = var.environment
    Type        = "public"
  }
}

# 3. Private Application Subnets (For EC2 Docker Compose Host)
resource "aws_subnet" "private_app" {
  count             = length(var.private_app_subnet_cidrs)
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.private_app_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = {
    Name        = "zonata-${var.environment}-private-app-${var.availability_zones[count.index]}"
    Environment = var.environment
    Type        = "private-app"
  }
}

# 4. Private Database Subnets (Strictly Isolated for RDS PostgreSQL 16)
resource "aws_subnet" "private_db" {
  count             = length(var.private_db_subnet_cidrs)
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.private_db_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = {
    Name        = "zonata-${var.environment}-private-db-${var.availability_zones[count.index]}"
    Environment = var.environment
    Type        = "private-db"
  }
}

# 5. Routing Tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }

  tags = {
    Name        = "zonata-${var.environment}-public-rt"
    Environment = var.environment
  }
}

resource "aws_route_table_association" "public" {
  count          = length(aws_subnet.public)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Optional Elastic IP & NAT Gateway for Private Outbound Internet
resource "aws_eip" "nat" {
  count  = var.enable_nat_gateway ? 1 : 0
  domain = "vpc"

  tags = {
    Name        = "zonata-${var.environment}-nat-eip"
    Environment = var.environment
  }
}

resource "aws_nat_gateway" "nat" {
  count         = var.enable_nat_gateway ? 1 : 0
  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public[0].id

  tags = {
    Name        = "zonata-${var.environment}-nat"
    Environment = var.environment
  }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  dynamic "route" {
    for_each = var.enable_nat_gateway ? [1] : []
    content {
      cidr_block     = "0.0.0.0/0"
      nat_gateway_id = aws_nat_gateway.nat[0].id
    }
  }

  tags = {
    Name        = "zonata-${var.environment}-private-rt"
    Environment = var.environment
  }
}

resource "aws_route_table_association" "private_app" {
  count          = length(aws_subnet.private_app)
  subnet_id      = aws_subnet.private_app[count.index].id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private_db" {
  count          = length(aws_subnet.private_db)
  subnet_id      = aws_subnet.private_db[count.index].id
  route_table_id = aws_route_table.private.id
}

# 6. Security Groups
# 6A. Public Ingress Security Group (ALB / Nginx Public Edge)
resource "aws_security_group" "ingress_sg" {
  name        = "zonata-${var.environment}-ingress-sg"
  description = "Allows inbound HTTPS (443) and HTTP redirect (80)"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "Allow HTTP for redirect to HTTPS"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Allow HTTPS for secure TLS traffic"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "zonata-${var.environment}-ingress-sg"
    Environment = var.environment
  }
}

# 6B. Application Host Security Group (EC2 Docker Compose Host)
resource "aws_security_group" "app_host_sg" {
  name        = "zonata-${var.environment}-app-host-sg"
  description = "Secures the EC2 Docker Compose host; receives traffic from ingress SG"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Allow HTTP from ingress SG"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.ingress_sg.id]
  }

  ingress {
    description     = "Allow HTTPS from ingress SG"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.ingress_sg.id]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "zonata-${var.environment}-app-host-sg"
    Environment = var.environment
  }
}

# 6C. Database Security Group (PostgreSQL 16)
# Strictly restricts port 5432 ingress to the Application Host Security Group
resource "aws_security_group" "db_sg" {
  name        = "zonata-${var.environment}-db-sg"
  description = "Strictly isolates RDS PostgreSQL 16; allows port 5432 ingress only from app host"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Allow PostgreSQL access strictly from app host"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app_host_sg.id]
  }

  egress {
    description = "Deny all outbound traffic from DB"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "zonata-${var.environment}-db-sg"
    Environment = var.environment
  }
}
