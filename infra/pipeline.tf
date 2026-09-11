resource "aws_s3_bucket" "artifacts" {

  count  = var.enable_pipeline ? 1 : 0
  bucket = "${local.name}-pipeline-${local.suffix}"

}
resource "aws_s3_bucket_public_access_block" "artifacts" {

  count                   = var.enable_pipeline ? 1 : 0
  bucket                  = aws_s3_bucket.artifacts[0].id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true

}
resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {

  count  = var.enable_pipeline ? 1 : 0
  bucket = aws_s3_bucket.artifacts[0].id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }

}
resource "aws_s3_bucket_versioning" "artifacts" {

  count  = var.enable_pipeline ? 1 : 0
  bucket = aws_s3_bucket.artifacts[0].id
  versioning_configuration {
    status = "Enabled"
  }

}
resource "aws_s3_bucket_lifecycle_configuration" "artifacts" {

  count  = var.enable_pipeline ? 1 : 0
  bucket = aws_s3_bucket.artifacts[0].id
  rule {
    id     = "expire-builds"
    status = "Enabled"
    filter {

    }
    expiration {
      days = 14
    }
    noncurrent_version_expiration {
      noncurrent_days = 7
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }

  }

}
resource "aws_s3_bucket_policy" "artifacts" {

  count  = var.enable_pipeline ? 1 : 0
  bucket = aws_s3_bucket.artifacts[0].id
  policy = jsonencode({
    Version = "2012-10-17", Statement = [{
      Effect = "Deny", Principal = "*", Action = "s3:*", Resource = [aws_s3_bucket.artifacts[0].arn, "${aws_s3_bucket.artifacts[0].arn}/*"], Condition = {
        Bool = {
          "aws:SecureTransport" = "false"
        }
      }
    }]
  })

}
resource "aws_cloudwatch_log_group" "build" {

  count             = var.enable_pipeline ? 1 : 0
  name              = "/aws/codebuild/${local.name}"
  retention_in_days = 14

}
resource "aws_iam_role" "pipeline" {

  count = var.enable_pipeline ? 1 : 0
  name  = "${local.name}-pipeline"
  assume_role_policy = jsonencode({
    Version = "2012-10-17", Statement = [{
      Effect = "Allow", Principal = {
        Service = "codepipeline.amazonaws.com"
      }, Action = "sts:AssumeRole"
    }]
  })

}
resource "aws_iam_role" "build" {

  for_each = var.enable_pipeline ? toset(["test", "deploy"]) : toset([])
  name     = "${local.name}-build-${each.key}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17", Statement = [{
      Effect = "Allow", Principal = {
        Service = "codebuild.amazonaws.com"
      }, Action = "sts:AssumeRole"
    }]
  })

}
resource "aws_iam_role_policy" "build_common" {

  for_each = aws_iam_role.build
  role     = each.value.id
  policy = jsonencode({
    Version = "2012-10-17", Statement = [
      {
        Effect = "Allow", Action = ["s3:GetObject", "s3:GetObjectVersion", "s3:PutObject"], Resource = "${aws_s3_bucket.artifacts[0].arn}/*"
      },
      {
        Effect = "Allow", Action = ["s3:GetBucketLocation", "s3:GetBucketVersioning"], Resource = aws_s3_bucket.artifacts[0].arn
      },
      {
        Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"], Resource = "${aws_cloudwatch_log_group.build[0].arn}:*"
      }
    ]
  })

}
resource "aws_iam_role_policy" "deploy" {

  count = var.enable_pipeline ? 1 : 0
  role  = aws_iam_role.build["deploy"].id
  policy = jsonencode({
    Version = "2012-10-17", Statement = [
      {
        # The deployment helper uses FunctionUpdated, whose poll is GetFunctionConfiguration.
        Effect = "Allow", Action = ["lambda:UpdateFunctionCode", "lambda:GetFunctionConfiguration"], Resource = [for fn in aws_lambda_function.app : fn.arn]
      },
      {
        Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"], Resource = "${aws_s3_bucket.frontend.arn}/*"
      },
      {
        Effect = "Allow", Action = "s3:ListBucket", Resource = aws_s3_bucket.frontend.arn
      },
      {
        Effect = "Allow", Action = "cloudfront:CreateInvalidation", Resource = aws_cloudfront_distribution.frontend.arn
      }
    ]
  })

}
resource "aws_codebuild_project" "app" {

  for_each       = var.enable_pipeline ? toset(["test", "deploy"]) : toset([])
  name           = "${local.name}-${each.key}"
  service_role   = aws_iam_role.build[each.key].arn
  build_timeout  = 15
  queued_timeout = 30
  artifacts {
    type = "CODEPIPELINE"
  }
  source {
    type      = "CODEPIPELINE"
    buildspec = each.key == "test" ? "buildspec.yml" : "buildspec-deploy.yml"

  }
  environment {

    compute_type    = "BUILD_GENERAL1_SMALL"
    image           = "aws/codebuild/standard:7.0"
    type            = "LINUX_CONTAINER"
    privileged_mode = false
    environment_variable {
      name  = "FRONTEND_BUCKET"
      value = aws_s3_bucket.frontend.id

    }
    environment_variable {
      name  = "DISTRIBUTION_ID"
      value = aws_cloudfront_distribution.frontend.id

    }
    environment_variable {
      name = "FUNCTION_NAMES"
      value = jsonencode({
        for key, fn in aws_lambda_function.app : key => fn.function_name
      })

    }
    environment_variable {
      name = "CLIENT_CONFIG"
      value = jsonencode({
        mode = "live", apiUrl = aws_apigatewayv2_api.api.api_endpoint, cognitoDomain = "https://${aws_cognito_user_pool_domain.analysts.domain}.auth.${var.region}.amazoncognito.com", clientId = aws_cognito_user_pool_client.web.id, scope = "openid threatlens/read threatlens/write"
      })

    }

  }
  logs_config {
    cloudwatch_logs {
      group_name  = aws_cloudwatch_log_group.build[0].name
      stream_name = each.key

    }

  }

}
resource "aws_iam_role_policy" "pipeline" {

  count = var.enable_pipeline ? 1 : 0
  role  = aws_iam_role.pipeline[0].id
  policy = jsonencode({
    Version = "2012-10-17", Statement = [
      {
        Effect = "Allow", Action = ["codeconnections:UseConnection", "codestar-connections:UseConnection"], Resource = var.connection_arn
      },
      {
        Effect = "Allow", Action = ["s3:GetObject", "s3:GetObjectVersion", "s3:PutObject"], Resource = "${aws_s3_bucket.artifacts[0].arn}/*"
      },
      {
        Effect = "Allow", Action = ["s3:GetBucketLocation", "s3:GetBucketVersioning"], Resource = aws_s3_bucket.artifacts[0].arn
      },
      {
        Effect = "Allow", Action = ["codebuild:StartBuild", "codebuild:BatchGetBuilds"], Resource = [for build in aws_codebuild_project.app : build.arn]
      }
    ]
  })

}
resource "aws_codepipeline" "app" {

  count          = var.enable_pipeline ? 1 : 0
  name           = local.name
  role_arn       = aws_iam_role.pipeline[0].arn
  pipeline_type  = "V2"
  execution_mode = "QUEUED"
  artifact_store {
    location = aws_s3_bucket.artifacts[0].id
    type     = "S3"

  }
  stage {
    name = "Source"
    action {
      name             = "GitHub"
      category         = "Source"
      owner            = "AWS"
      provider         = "CodeStarSourceConnection"
      version          = "1"
      output_artifacts = ["Source"]
      configuration = {
        ConnectionArn = var.connection_arn, FullRepositoryId = var.repository_id, BranchName = var.branch_name, DetectChanges = "true"
      }

    }

  }
  stage {
    name = "Quality"
    action {
      name             = "TestBuildValidate"
      category         = "Build"
      owner            = "AWS"
      provider         = "CodeBuild"
      version          = "1"
      input_artifacts  = ["Source"]
      output_artifacts = ["Build"]
      configuration = {
        ProjectName = aws_codebuild_project.app["test"].name
      }

    }

  }
  stage {
    name = "Review"
    action {
      name     = "ApproveDeployment"
      category = "Approval"
      owner    = "AWS"
      provider = "Manual"
      version  = "1"

    }

  }
  stage {
    name = "Deploy"
    action {
      name            = "PublishApplication"
      category        = "Build"
      owner           = "AWS"
      provider        = "CodeBuild"
      version         = "1"
      input_artifacts = ["Build"]
      configuration = {
        ProjectName = aws_codebuild_project.app["deploy"].name
      }

    }

  }
  lifecycle {
    precondition {
      condition     = var.connection_arn != "" && can(regex("^[^/]+/[^/]+$", var.repository_id))
      error_message = "Provide an available CodeConnections ARN and owner/repository before enabling the pipeline."

    }

  }

}
