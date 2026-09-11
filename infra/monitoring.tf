resource "aws_cloudwatch_metric_alarm" "dlq" {

  for_each = {
    ingest = aws_sqs_queue.dlq.name, notification = aws_sqs_queue.notification_failures.name
  }
  alarm_name  = "${local.name}-${each.key}-dlq-not-empty"
  namespace   = "AWS/SQS"
  metric_name = "ApproximateNumberOfMessagesVisible"
  dimensions = {
    QueueName = each.value
  }
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 1
  comparison_operator = "GreaterThanThreshold"
  threshold           = 0
  treat_missing_data  = "notBreaching"

}
resource "aws_cloudwatch_metric_alarm" "errors" {

  for_each    = local.lambda_services
  alarm_name  = "${local.name}-${each.key}-errors"
  namespace   = "AWS/Lambda"
  metric_name = "Errors"
  dimensions = {
    FunctionName = aws_lambda_function.app[each.key].function_name
  }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  comparison_operator = "GreaterThanThreshold"
  threshold           = 0
  treat_missing_data  = "notBreaching"

}
resource "aws_cloudwatch_metric_alarm" "queue_age" {

  alarm_name  = "${local.name}-queue-age"
  namespace   = "AWS/SQS"
  metric_name = "ApproximateAgeOfOldestMessage"
  dimensions = {
    QueueName = aws_sqs_queue.events.name
  }
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 3
  comparison_operator = "GreaterThanThreshold"
  threshold           = 300
  treat_missing_data  = "notBreaching"

}
