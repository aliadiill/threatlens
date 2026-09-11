resource "aws_dynamodb_table" "incidents" {

  name         = "${local.name}-incidents"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"
  attribute {
    name = "PK"
    type = "S"

  }
  attribute {
    name = "SK"
    type = "S"

  }
  attribute {
    name = "GSI1PK"
    type = "S"

  }
  attribute {
    name = "GSI1SK"
    type = "S"

  }
  global_secondary_index {

    name            = "timeline"
    hash_key        = "GSI1PK"
    range_key       = "GSI1SK"
    projection_type = "ALL"

  }
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"
  server_side_encryption {
    enabled = true
  }
  point_in_time_recovery {
    enabled                 = true
    recovery_period_in_days = 7

  }

}
resource "aws_sqs_queue" "dlq" {
  name                      = "${local.name}-dlq"
  message_retention_seconds = 1209600
  sqs_managed_sse_enabled   = true

}
resource "aws_sqs_queue" "events" {

  name                       = "${local.name}-events"
  visibility_timeout_seconds = 180
  message_retention_seconds  = 345600
  sqs_managed_sse_enabled    = true
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn, maxReceiveCount = 5
  })

}
resource "aws_sqs_queue_redrive_allow_policy" "dlq" {

  queue_url = aws_sqs_queue.dlq.id
  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue", sourceQueueArns = [aws_sqs_queue.events.arn]
  })

}
resource "aws_sqs_queue" "notification_failures" {
  name                      = "${local.name}-notification-failures"
  message_retention_seconds = 1209600
  sqs_managed_sse_enabled   = true

}
resource "aws_cloudwatch_event_bus" "security" {
  name = "${local.name}-events"
}
resource "aws_cloudwatch_event_rule" "ingest" {

  name           = "${local.name}-ingest"
  event_bus_name = aws_cloudwatch_event_bus.security.name
  event_pattern = jsonencode({
    source = ["threatlens.demo", "aws.iam", "aws.ec2", "aws.signin", "aws.cloudtrail"]
  })

}
resource "aws_cloudwatch_event_target" "queue" {

  rule           = aws_cloudwatch_event_rule.ingest.name
  event_bus_name = aws_cloudwatch_event_bus.security.name
  arn            = aws_sqs_queue.events.arn
  retry_policy {
    maximum_event_age_in_seconds = 3600
    maximum_retry_attempts       = 10

  }
  dead_letter_config {
    arn = aws_sqs_queue.dlq.arn
  }

}
resource "aws_sqs_queue_policy" "events" {

  queue_url = aws_sqs_queue.events.id
  policy = jsonencode({
    Version = "2012-10-17", Statement = [{
      Effect = "Allow", Principal = {
        Service = "events.amazonaws.com"
        }, Action = "sqs:SendMessage", Resource = aws_sqs_queue.events.arn, Condition = {
        ArnEquals = {
          "aws:SourceArn" = aws_cloudwatch_event_rule.ingest.arn
        }
      }
    }]
  })

}
resource "aws_sqs_queue_policy" "event_dlq" {

  queue_url = aws_sqs_queue.dlq.id
  policy = jsonencode({
    Version = "2012-10-17", Statement = [{
      Effect = "Allow", Principal = {
        Service = "events.amazonaws.com"
        }, Action = "sqs:SendMessage", Resource = aws_sqs_queue.dlq.arn, Condition = {
        ArnEquals = {
          "aws:SourceArn" = aws_cloudwatch_event_rule.ingest.arn
        }
      }
    }]
  })

}
resource "aws_cloudwatch_event_rule" "cloudtrail" {

  count = var.enable_cloudtrail_input ? 1 : 0
  name  = "${local.name}-cloudtrail-input"
  event_pattern = jsonencode({
    source = ["aws.iam", "aws.ec2", "aws.signin", "aws.cloudtrail"], "detail-type" = ["AWS API Call via CloudTrail", "AWS Console Sign In via CloudTrail"]
  })

}
resource "aws_iam_role" "forward" {

  count = var.enable_cloudtrail_input ? 1 : 0
  name  = "${local.name}-forward-events"
  assume_role_policy = jsonencode({
    Version = "2012-10-17", Statement = [{
      Effect = "Allow", Principal = {
        Service = "events.amazonaws.com"
        }, Action = "sts:AssumeRole", Condition = {
        StringEquals = {
          "aws:SourceAccount" = data.aws_caller_identity.current.account_id
        }
      }
    }]
  })

}
resource "aws_iam_role_policy" "forward" {

  count = var.enable_cloudtrail_input ? 1 : 0
  role  = aws_iam_role.forward[0].id
  policy = jsonencode({
    Version = "2012-10-17", Statement = [{
      Effect = "Allow", Action = "events:PutEvents", Resource = aws_cloudwatch_event_bus.security.arn
    }]
  })

}
resource "aws_cloudwatch_event_target" "cloudtrail" {

  count    = var.enable_cloudtrail_input ? 1 : 0
  rule     = aws_cloudwatch_event_rule.cloudtrail[0].name
  arn      = aws_cloudwatch_event_bus.security.arn
  role_arn = aws_iam_role.forward[0].arn

}
resource "aws_kms_key" "notifications" {

  description             = "ThreatLens notification encryption"
  enable_key_rotation     = true
  deletion_window_in_days = 7

}
resource "aws_sns_topic" "incidents" {
  name              = "${local.name}-incidents"
  kms_master_key_id = aws_kms_key.notifications.arn

}
resource "aws_sns_topic_subscription" "email" {

  count     = var.notifications_enabled && nonsensitive(var.notification_email != "") ? 1 : 0
  topic_arn = aws_sns_topic.incidents.arn
  protocol  = "email"
  endpoint  = var.notification_email

}
