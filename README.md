# AVR — AI Video Production Studio

AVR nghiên cứu chủ đề, kiểm chứng claim, tạo semantic storyboard và render video social bằng Remotion.

## Local development

```sh
cp .env.example .env
make up
make migrate
make verify-dev
```

API health: `http://localhost:8000/health`. Frontend: `http://localhost:3000`.

Máy không có GPU vẫn chạy đầy đủ stack development; service Ollama là profile `gpu` opt-in và không khởi động mặc định. Các unit test không yêu cầu Ollama/GPU.
