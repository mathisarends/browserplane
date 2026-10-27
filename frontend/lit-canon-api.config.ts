import { defineConfig } from "lit-canon-api";

export default defineConfig({
  input: "../schemas/backend-openapi.json",
  output: "generated-backend/src/canon",
  prettier: { printWidth: 100 },
});
