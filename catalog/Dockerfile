FROM mcr.microsoft.com/dotnet/sdk:8.0.407-bookworm-slim AS build
WORKDIR /source
COPY catalog/ ./
RUN dotnet publish Catalog.csproj -c Release -o /out --self-contained false

FROM mcr.microsoft.com/dotnet/aspnet:8.0.14-bookworm-slim
WORKDIR /app
COPY --from=build /out/ ./
RUN mkdir /state && chown 1654:1654 /state
USER 1654
ENV PORT=18132 BIND_ADDRESS=0.0.0.0 CATALOG_STATE=/state
ENTRYPOINT ["dotnet", "Catalog.dll", "serve"]
