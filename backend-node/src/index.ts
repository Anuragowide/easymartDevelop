import { startServer } from "./server";

startServer()
  .then(() => console.log("⚡ Easymart Node backend started"))
  .catch((err) => {
    console.error("❌ Failed to start server", err);
    process.exit(1);
  });
