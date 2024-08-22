FROM alpine:latest

# Add a script to print environment variables in a more readable format
RUN echo '#!/bin/sh' > /print_env.sh && \
    echo 'env | sort | sed "s/^/export /"' >> /print_env.sh && \
    chmod +x /print_env.sh

# Set the entry point to our script
ENTRYPOINT ["/print_env.sh"]