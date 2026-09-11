"""Publish an already-built artifact using scoped, temporary AWS credentials."""
import json
import mimetypes
import os
from pathlib import Path


def main():
    import boto3
    root = Path(__file__).resolve().parents[1]
    bucket, distribution = os.environ["FRONTEND_BUCKET"], os.environ["DISTRIBUTION_ID"]
    names, config = json.loads(os.environ["FUNCTION_NAMES"]), json.loads(os.environ["CLIENT_CONFIG"])
    if config.get("mode") != "live" or not str(config.get("apiUrl", "")).startswith("https://"):
        raise ValueError("Deployment requires a valid live HTTPS client config")
    (root / "dist" / "config.json").write_text(json.dumps(config), encoding="utf-8")
    functions = boto3.client("lambda")
    archive = (root / "build" / "backend.zip").read_bytes()
    for name in names.values():
        functions.update_function_code(FunctionName=name, ZipFile=archive)
        functions.get_waiter("function_updated_v2").wait(FunctionName=name)
    s3 = boto3.client("s3")
    # Hashed assets first; entry point last. Retain old hashes for rollback/cache safety.
    paths = sorted((root / "dist").rglob("*"), key=lambda p: p.name == "index.html")
    for path in paths:
        if path.is_file():
            key = path.relative_to(root / "dist").as_posix()
            mime = "text/javascript" if path.suffix == ".js" else mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            s3.put_object(Bucket=bucket, Key=key, Body=path.read_bytes(), ContentType=mime, CacheControl="no-cache, no-store" if key in {"index.html", "config.json"} else "public,max-age=31536000,immutable", ServerSideEncryption="AES256")
    import time
    boto3.client("cloudfront").create_invalidation(DistributionId=distribution, InvalidationBatch={"Paths": {"Quantity": 3, "Items": ["/", "/index.html", "/config.json"]}, "CallerReference": str(time.time_ns())})
    print("Published application; run authenticated smoke tests before declaring deployment successful")


if __name__ == "__main__":
    main()
