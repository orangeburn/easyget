import { ClueTable } from '../ClueList/ClueTable';
import './MainGrid.css';

export const MainGrid: React.FC = () => {

  return (
    <div className="main-grid-container simplified">
      <div className="clue-list-section">
        <ClueTable />
      </div>
    </div>
  );
};
