FROM golang:1.25-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -o /out/server ./cmd/server \
 && CGO_ENABLED=0 GOOS=linux go build -trimpath -o /out/worker ./cmd/worker

FROM alpine:3.21
RUN apk add --no-cache ca-certificates
COPY --from=build /out/server /server
COPY --from=build /out/worker /worker
EXPOSE 8080
CMD ["/server"]
