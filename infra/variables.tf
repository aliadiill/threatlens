variable "region" {
  type    = string
  default = "us-east-1"

}
variable "lambda_reserved_concurrency" {
  type        = number
  default     = -1
  description = "-1 uses the account pool; use 2 per function only when the account has sufficient unreserved concurrency. SQS remains capped at 2."
  validation {
    condition     = var.lambda_reserved_concurrency == -1 || var.lambda_reserved_concurrency >= 2
    error_message = "Use -1 or at least 2, matching the SQS mapping maximum concurrency."
  }
}
variable "environment" {
  type    = string
  default = "dev"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,12}$", var.environment))
    error_message = "Use a short lowercase environment name."

  }

}
variable "enable_cloudtrail_input" {
  type        = bool
  default     = false
  description = "Forward existing CloudTrail management events from the default bus. Does not enable or create a trail."

}
variable "notifications_enabled" {
  type        = bool
  default     = false
  description = "Opt in to real SNS publishes. No email subscription is created unless notification_email is provided."

}
variable "notification_email" {
  type        = string
  default     = ""
  sensitive   = true
  description = "Only an explicitly authorized recipient; requires SNS email confirmation."

}
variable "connection_arn" {
  type        = string
  default     = ""
  description = "Existing AVAILABLE CodeConnections ARN authorized for the source repository. Empty disables pipeline provisioning."

}
variable "repository_id" {
  type        = string
  default     = ""
  description = "GitHub owner/repository for CodePipeline."

}
variable "branch_name" {
  type    = string
  default = "main"

}
variable "enable_pipeline" {
  type    = bool
  default = false

}
variable "frontend_build_path" {
  type        = string
  default     = "../dist"
  description = "Frontend assets are uploaded by the deployment script/CodeBuild, not Terraform."

}
