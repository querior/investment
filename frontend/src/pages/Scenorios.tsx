import React, { useEffect } from 'react';
import { Card, Table, Typography } from 'antd';
import { useDispatch, useSelector } from 'react-redux';
import { fetchScenarios } from '../features/scenario/reducer';
import type { RootState } from '../store/reducers';

export default function Dashboard() {
  const dispatch = useDispatch();
  const { items, loading, error } = useSelector((s: RootState) => s.scenarios);

  useEffect(() => {
    dispatch(fetchScenarios());
  }, [dispatch]);

  return (
    <div className="space-y-4">
      <Typography.Title level={3} className="!m-0">Scenari</Typography.Title>

      {error && <div className="text-red-600">{error}</div>}

      <Card>
        <Table
          rowKey="id"
          loading={loading}
          dataSource={items}
          columns={[
            { title: 'ID', dataIndex: 'id', width: 80 },
            { title: 'Nome', dataIndex: 'name' },
            { title: 'Descrizione', dataIndex: 'description' },
          ]}
          pagination={{ pageSize: 10 }}
        />
      </Card>
    </div>
  );
}
