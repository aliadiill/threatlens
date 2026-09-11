data "archive_file" "backend" {

  type        = "zip"
  output_path = "${path.module}/../build/backend.zip"
  dynamic "source" {

    for_each = fileset("${path.module}/../backend", "*.py")
    content {

      content  = file("${path.module}/../backend/${source.value}")
      filename = "backend/${source.value}"

    }

  }

}
resource "aws_cloudwatch_log_group" "lambda" {

  for_each          = local.lambda_services
  name              = "/aws/lambda/${local.name}-${each.key}"
  retention_in_days = 14

}
resource "aws_iam_role" "lambda" {

  for_each = local.lambda_services
  name     = "${local.name}-${each.key}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17", Statement = [{
      Effect = "Allow", Principal = {
        Service = "lambda.amazonaws.com"
      }, Action = "sts:AssumeRole"
    }]
  })

}
resource "aws_iam_role_policy" "logs" {

  for_each = local.lambda_services
  role     = aws_iam_role.lambda[each.key].id
  policy = jsonencode({
    Version = "2012-10-17", Statement = [{
      Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"], Resource = "${aws_cloudwatch_log_group.lambda[each.key].arn}:*"
    }]
  })

}
resource "aws_iam_role_policy" "processor" {

  role = aws_iam_role.lambda["processor"].id
  policy = jsonencode({
    Version = "2012-10-17", Statement = [
      {
        Effect = "Allow", Action = ["dynamodb:PutItem", "dynamodb:GetItem"], Resource = aws_dynamodb_table.incidents.arn
      },
      {
        Effect = "Allow", Action = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"], Resource = aws_sqs_queue.events.arn
      }
    ]
  })

}
resource "aws_iam_role_policy" "api" {

  role = aws_iam_role.lambda["api"].id
  policy = jsonencode({
    Version = "2012-10-17", Statement = [
      {
        Effect = "Allow", Action = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:PutItem", "dynamodb:UpdateItem"], Resource = aws_dynamodb_table.incidents.arn, Condition = {
          "ForAllValues:StringLike" = {
            "dynamodb:LeadingKeys" = ["INCIDENT#*"]
          }
        }
      },
      {
        Effect = "Allow", Action = "dynamodb:Query", Resource = "${aws_dynamodb_table.incidents.arn}/index/timeline"
      }
    ]
  })

}
resource "aws_iam_role_policy" "notifier" {

  role = aws_iam_role.lambda["notifier"].id
  policy = jsonencode({
    Version = "2012-10-17", Statement = [
      {
        Effect = "Allow", Action = ["dynamodb:GetItem", "dynamodb:UpdateItem"], Resource = aws_dynamodb_table.incidents.arn, Condition = {
          "ForAllValues:StringLike" = {
            "dynamodb:LeadingKeys" = ["OUTBOX#*"]
          }
        }
      },
      {
        Effect = "Allow", Action = ["dynamodb:GetRecords", "dynamodb:GetShardIterator", "dynamodb:DescribeStream"], Resource = aws_dynamodb_table.incidents.stream_arn
      },
      {
        Effect = "Allow", Action = "dynamodb:ListStreams", Resource = "*"
      },
      {
        Effect = "Allow", Action = "sns:Publish", Resource = aws_sns_topic.incidents.arn
      },
      {
        Effect = "Allow", Action = ["kms:Decrypt", "kms:GenerateDataKey*"], Resource = aws_kms_key.notifications.arn
      },
      {
        Effect = "Allow", Action = "sqs:SendMessage", Resource = aws_sqs_queue.notification_failures.arn
      }
    ]
  })

}
resource "aws_lambda_function" "app" {

  for_each                       = local.lambda_services
  function_name                  = "${local.name}-${each.key}"
  role                           = aws_iam_role.lambda[each.key].arn
  runtime                        = "python3.12"
  handler                        = "backend.${each.key}.handler"
  filename                       = data.archive_file.backend.output_path
  source_code_hash               = data.archive_file.backend.output_base64sha256
  timeout                        = 30
  memory_size                    = 256
  reserved_concurrent_executions = var.lambda_reserved_concurrency
  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.incidents.name, TOPIC_ARN = aws_sns_topic.incidents.arn, NOTIFICATIONS_ENABLED = tostring(var.notifications_enabled)
    }
  }
  depends_on = [aws_iam_role_policy.logs, aws_cloudwatch_log_group.lambda, aws_iam_role_policy.api, aws_iam_role_policy.processor, aws_iam_role_policy.notifier]

}
resource "aws_lambda_event_source_mapping" "queue" {

  event_source_arn        = aws_sqs_queue.events.arn
  function_name           = aws_lambda_function.app["processor"].arn
  batch_size              = 10
  function_response_types = ["ReportBatchItemFailures"]
  scaling_config {
    maximum_concurrency = 2
  }

}
resource "aws_lambda_event_source_mapping" "outbox" {

  event_source_arn               = aws_dynamodb_table.incidents.stream_arn
  function_name                  = aws_lambda_function.app["notifier"].arn
  starting_position              = "TRIM_HORIZON"
  batch_size                     = 10
  bisect_batch_on_function_error = true
  maximum_retry_attempts         = 5
  maximum_record_age_in_seconds  = 3600
  function_response_types        = ["ReportBatchItemFailures"]
  destination_config {
    on_failure {
      destination_arn = aws_sqs_queue.notification_failures.arn
    }
  }
  filter_criteria {
    filter {
      pattern = jsonencode({
        eventName = ["INSERT"], dynamodb = {
          NewImage = {
            entity = {
              S = ["OUTBOX"]
            }
          }
        }
      })
    }
  }

}
