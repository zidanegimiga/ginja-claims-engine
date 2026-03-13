import type { Config } from "jest";
import nextJest from "next/jest.js";

interface CustomConfig extends Config {
  setupFilesAfterFramework?: string[];
}

const createJestConfig = nextJest({ dir: "./" });

const config: CustomConfig = {
  coverageProvider: "v8",
  testEnvironment:  "jsdom",
  setupFilesAfterFramework: ["<rootDir>/jest.setup.ts"],
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/src/$1",
  },
};

export default createJestConfig(config);