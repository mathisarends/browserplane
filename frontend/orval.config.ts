import { defineConfig } from "orval";

export default defineConfig({
  backend: {
    input: { target: "../schemas/backend-openapi.json" },
    output: {
      target: "generated-backend/src/generated/backend.ts",
      schemas: "generated-backend/src/generated/models",
      client: "fetch",
      mode: "split",
      clean: ["generated-backend/src/generated"],
    },
  },
});
