FROM nginx

ARG SERVER_UID
ARG SERVER_GID

# Change ownership so the default configuration can be modified.
RUN chown -R $SERVER_UID:$SERVER_GID /etc/nginx/conf.d

# Use a non-root user.
USER $SERVER_UID:$SERVER_GID
