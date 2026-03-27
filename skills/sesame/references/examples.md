# Sesame Usage Examples

## REST API Patterns

### GitHub API

```bash
# Get authenticated user info
secretctl request GET "https://api.github.com/user" --raw

# List repositories
secretctl request GET "https://api.github.com/user/repos?per_page=10" --raw | jq '.[].full_name'

# Create an issue
secretctl request POST "https://api.github.com/repos/owner/repo/issues" \
  -H "Content-Type: application/json" \
  -d '{"title": "Bug report", "body": "Description of the issue"}'

# Get pull request details
secretctl request GET "https://api.github.com/repos/owner/repo/pulls/123" --raw
```

### OpenAI API

```bash
# Chat completion
secretctl request POST "https://api.openai.com/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-4", "messages": [{"role": "user", "content": "Hello"}]}'

# List models
secretctl request GET "https://api.openai.com/v1/models" --raw | jq '.data[].id'

# Create embedding
secretctl request POST "https://api.openai.com/v1/embeddings" \
  -H "Content-Type: application/json" \
  -d '{"model": "text-embedding-3-small", "input": "Sample text"}'
```

### Slack API

```bash
# Post a message
secretctl request POST "https://slack.com/api/chat.postMessage" \
  -H "Content-Type: application/json" \
  -d '{"channel": "C01234567", "text": "Hello from Sesame!"}'

# List channels
secretctl request GET "https://slack.com/api/conversations.list" --raw | jq '.channels[].name'
```

### Stripe API

```bash
# List customers (Stripe uses Bearer token auth)
secretctl request GET "https://api.stripe.com/v1/customers?limit=10" --raw

# Create a customer (form-encoded body)
secretctl request POST "https://api.stripe.com/v1/customers" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "email=customer@example.com&name=John+Doe"
```

### Twilio API

```bash
# Send SMS (Twilio uses Basic auth)
secretctl request POST "https://api.twilio.com/2010-04-01/Accounts/ACXXXXX/Messages.json" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "To=+1234567890&From=+0987654321&Body=Hello+from+Sesame"
```

## Common Patterns

### Checking response status before proceeding

```bash
# Capture the full response
RESPONSE=$(secretctl request GET "https://api.github.com/user")
STATUS=$(echo "$RESPONSE" | jq -r '.status_code')
BODY=$(echo "$RESPONSE" | jq -r '.body')

if [ "$STATUS" = "200" ]; then
  echo "Success: $BODY"
else
  echo "Error $STATUS: $BODY"
fi
```

### Piping raw output to jq

```bash
# Extract specific fields
secretctl request GET "https://api.github.com/user" --raw | jq '{login, email, public_repos}'

# Filter a list
secretctl request GET "https://api.github.com/user/repos?per_page=100" --raw | jq '[.[] | select(.language == "Python") | .full_name]'
```

### Sequential API calls

```bash
# Step 1: Create a resource
CREATE_RESPONSE=$(secretctl request POST "https://api.example.com/items" \
  -H "Content-Type: application/json" \
  -d '{"name": "New Item"}' --raw)
ITEM_ID=$(echo "$CREATE_RESPONSE" | jq -r '.id')

# Step 2: Update the resource
secretctl request PUT "https://api.example.com/items/$ITEM_ID" \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Item", "status": "active"}'
```

### Pagination

```bash
# Fetch paginated results
PAGE=1
while true; do
  RESPONSE=$(secretctl request GET "https://api.example.com/items?page=$PAGE&per_page=100" --raw)
  COUNT=$(echo "$RESPONSE" | jq 'length')
  echo "$RESPONSE" | jq '.[].name'

  if [ "$COUNT" -lt 100 ]; then
    break
  fi
  PAGE=$((PAGE + 1))
done
```
