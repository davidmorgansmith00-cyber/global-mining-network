import { useEffect, useState } from "react";

type BlockSummary = {
  block_number: number;
  difficulty: string;
  reward_pool: string;
  miners_count: number;
  completion_time: string;
};

export default function ChainExplorer(): JSX.Element {
  const [blocks, setBlocks] = useState<BlockSummary[]>([]);

  useEffect(() => {
    fetch("/api/v1/explorer/blocks?limit=50&offset=0")
      .then((res) => res.json())
      .then((payload) => setBlocks(payload.items ?? []))
      .catch(() => setBlocks([]));
  }, []);

  return (
    <main>
      <h1>Chain Explorer</h1>
      <table>
        <thead>
          <tr>
            <th>Block</th>
            <th>Difficulty</th>
            <th>Reward Pool</th>
            <th>Miners</th>
            <th>Finalized</th>
          </tr>
        </thead>
        <tbody>
          {blocks.map((block) => (
            <tr key={block.block_number}>
              <td>{block.block_number}</td>
              <td>{block.difficulty}</td>
              <td>{block.reward_pool}</td>
              <td>{block.miners_count}</td>
              <td>{block.completion_time}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
