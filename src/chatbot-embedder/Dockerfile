# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

FROM golang:1.23.0-alpine AS builder

RUN apk add --no-cache ca-certificates git

WORKDIR /src

# go.modとgo.sumをコピーして依存関係をダウンロード
COPY go.mod go.sum* ./
RUN go mod download

# ソースコードをコピー
COPY . .

# ビルド
RUN CGO_ENABLED=0 GOOS=linux go build -o /chatbot-embedder .

# 最小イメージ
FROM alpine:3.17.0

RUN apk add --no-cache ca-certificates

COPY --from=builder /chatbot-embedder /app/chatbot-embedder

WORKDIR /app

ENTRYPOINT ["/app/chatbot-embedder"]






