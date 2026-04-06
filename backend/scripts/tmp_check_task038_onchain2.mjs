import { Contract, JsonRpcProvider } from "ethers";

const provider = new JsonRpcProvider("http://127.0.0.1:7545");
const abi = [
  "function getBlockMeta(string taskID) view returns (bytes32 modelHash, uint256 accuracy, address aggregator, uint256 timestamp, uint256 revealDeadline, bool distributed)",
  "function getParticipants(string taskID) view returns (address[] participants)",
  "function getScoreCommits(string taskID) view returns (bytes32[] scoreCommits)",
];
const blockPublisher = new Contract("0x1d44a21a98644b00b7DC745b710CAC7b97e915bB", abi, provider);

const taskID = "task_038";
try {
  const meta = await blockPublisher.getBlockMeta(taskID);
  const participants = await blockPublisher.getParticipants(taskID);
  const commits = await blockPublisher.getScoreCommits(taskID);
  console.log(JSON.stringify({
    exists: true,
    modelHash: String(meta[0]),
    accuracy: meta[1].toString(),
    aggregator: String(meta[2]),
    timestamp: meta[3].toString(),
    revealDeadline: meta[4].toString(),
    distributed: Boolean(meta[5]),
    participants: participants.map((p) => String(p)),
    scoreCommitsCount: commits.length,
  }, null, 2));
} catch (e) {
  console.log(JSON.stringify({ exists: false, error: String(e?.shortMessage || e?.message || e) }, null, 2));
}
