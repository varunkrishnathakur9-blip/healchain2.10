const path = require("path");

module.exports = {
  networks: {
    development: {
      host: "127.0.0.1",
      port: 7545,
      network_id: "1337",
    },
  },
  contracts_build_directory: path.resolve(__dirname, "build", "contracts"),
  compilers: {
    solc: {
      version: "0.8.19",
    },
  },
};

