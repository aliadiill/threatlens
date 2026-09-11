output "frontend_url" {
  value = local.frontend_origin
}
output "frontend_bucket" {
  value = aws_s3_bucket.frontend.id
}
output "distribution_id" {
  value = aws_cloudfront_distribution.frontend.id
}
output "event_bus_name" {
  value = aws_cloudwatch_event_bus.security.name
}
output "incident_table" {
  value = aws_dynamodb_table.incidents.name
}
output "queue_url" {
  value = aws_sqs_queue.events.url
}
output "dlq_url" {
  value = aws_sqs_queue.dlq.url
}
output "user_pool_id" {
  value = aws_cognito_user_pool.analysts.id
}
output "client_config" {
  value = {

    mode = "live", apiUrl = aws_apigatewayv2_api.api.api_endpoint, cognitoDomain = "https://${aws_cognito_user_pool_domain.analysts.domain}.auth.${var.region}.amazoncognito.com", clientId = aws_cognito_user_pool_client.web.id, scope = "openid threatlens/read threatlens/write"

  }
}
output "function_names" {
  value = {
    for key, fn in aws_lambda_function.app : key => fn.function_name
  }
}
