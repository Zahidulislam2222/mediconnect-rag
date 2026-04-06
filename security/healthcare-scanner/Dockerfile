FROM alpine:3.21

RUN apk add --no-cache bash ripgrep jq nodejs

COPY scanner.sh /scanner.sh
RUN chmod +x /scanner.sh

ENTRYPOINT ["/scanner.sh"]
