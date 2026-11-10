import { defineRailway, project, service } from "railway/iac";
// This repository manages only its own resources in the environment. Other
// repositories export their own partial name.
// See https://docs.railway.com/infrastructure-as-code#multi-repo-projects
export const partial = "developer-api";
export default defineRailway(() => {
  const developerApi = service("developer-api", {
    build: { buildEnvironment: "V3", builder: "DOCKERFILE", dockerfilePath: "/Dockerfile" },
    healthcheck: "/readyz",
    healthcheckTimeout: 30,
    replicas: { "asia-southeast1-eqsg3a": 1 },
    deploy: { sleepApplication: true, restartPolicyMaxRetries: 3 },
  });

  return project("platform-developer", {
    variables: { managed: false },
    resources: [developerApi],
  });
});
