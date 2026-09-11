terraform {

  required_version = ">= 1.10, < 2.0"
  required_providers {

    aws = {
      source = "hashicorp/aws", version = "~> 6.0"
    }
    archive = {
      source = "hashicorp/archive", version = "~> 2.7"
    }
    random = {
      source = "hashicorp/random", version = "~> 3.7"
    }

  }

}
provider "aws" {

  region = var.region
  default_tags {
    tags = {
      Project = "ThreatLens", Environment = var.environment, Owner = "Portfolio"
    }
  }

}
data "aws_caller_identity" "current" {

}
data "aws_partition" "current" {

}
resource "random_id" "suffix" {
  byte_length = 4
}
locals {

  name            = "threatlens-${var.environment}"
  suffix          = random_id.suffix.hex
  lambda_services = toset(["processor", "api", "notifier"])
  frontend_origin = "https://${aws_cloudfront_distribution.frontend.domain_name}"

}
