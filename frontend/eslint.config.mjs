import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  {
    // Flat config has no built-in default ignore list the way `next lint`
    // does — plain `eslint .` will otherwise walk generated/build output
    // (e.g. .next/static/chunks, .next/types) and report on minified,
    // non-source code. This must be its own config object with only
    // `ignores` so it applies globally, before any other config below.
    ignores: [
      ".next/**",
      "node_modules/**",
      "out/**",
      "build/**",
      "next-env.d.ts",
    ],
  },
  ...compat.extends("next/core-web-vitals", "next/typescript"),
];

export default eslintConfig;