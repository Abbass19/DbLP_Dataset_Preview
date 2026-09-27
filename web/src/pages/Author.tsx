import { useParams } from "react-router-dom";

export default function Author() {
  const { authorId } = useParams();
  return (
    <div className="card">
      <h2>Author {authorId}</h2>
      <p>Author profile page lands here in P8 (polish).</p>
    </div>
  );
}
