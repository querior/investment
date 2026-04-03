import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import { Button, Form, Popconfirm, Space, Table, Tooltip } from "antd";
import {
	DeleteOutlined,
	EditOutlined,
	EyeOutlined,
	PlusOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import type { RootState } from "../../store/reducers";
import {
	fetchBacktestsRequest,
	clearLastCreatedId,
	deleteBacktestRequest,
} from "../../features/backtest/reducer";
import { BacktestDto } from "../../features/backtest/types";
import UpsertBacktestModal, { CreateFormValues } from "./UpsertBacktestModal";

type EditFormValues = {
	name: string;
	description?: string;
};

export default function Backtest() {
	const dispatch = useDispatch();
	const navigate = useNavigate();

	const { backtests, total, page, loading, lastCreatedId } = useSelector(
		(state: RootState) => state.backtest
	);

	const [upsertModalOpen, setUpsertModalOpen] = useState(false);
	const [editingBt, setEditingBt] = useState<BacktestDto | null>(null);
	const [createForm] = Form.useForm<CreateFormValues>();

	useEffect(() => {
		dispatch(clearLastCreatedId());
		dispatch(fetchBacktestsRequest());
	}, [dispatch]);

	useEffect(() => {
		if (lastCreatedId !== null) {
			setUpsertModalOpen(false);
			createForm.resetFields();
			navigate(`/analysis/backtest/${lastCreatedId}`);
			dispatch(clearLastCreatedId());
		}
	}, [lastCreatedId, navigate, createForm, dispatch]);

	const handleAdd = async () => {
		setEditingBt(null);
		setUpsertModalOpen(true);
	};

	const openEdit = (bt: BacktestDto) => {
		setEditingBt(bt);
		setUpsertModalOpen(true);
	};

	const columns: ColumnsType<BacktestDto> = [
		{ title: "Name", dataIndex: "name", key: "name" },
		{
			title: "Description",
			dataIndex: "description",
			key: "description",
			render: (v: string | null) => v ?? "—",
		},
		{ title: "Frequency", dataIndex: "frequency", key: "frequency" },
		{
			title: "Version",
			dataIndex: "strategy_version",
			key: "strategy_version",
		},
		{
			title: "Created at",
			dataIndex: "created_at",
			key: "created_at",
			render: (v: string) => new Date(v).toLocaleDateString("it-IT"),
		},
		{
			title: "Updated at",
			dataIndex: "updated_at",
			key: "updated_at",
			render: (v: string) => new Date(v).toLocaleDateString("it-IT"),
		},
		{
			title: "Actions",
			key: "actions",
			align: "center",
			render: (_: unknown, bt: BacktestDto) => (
				<Space>
					<Tooltip title="View">
						<Button
							type="text"
							icon={<EyeOutlined />}
							onClick={() => navigate(`/analysis/backtest/${bt.id}`)}
						/>
					</Tooltip>
					<Tooltip title="Edit">
						<Button
							type="text"
							icon={<EditOutlined />}
							onClick={() => openEdit(bt)}
						/>
					</Tooltip>
					<Tooltip title="Delete">
						<Popconfirm
							title="Delete this backtest?"
							okText="Delete"
							cancelText="Cancel"
							okButtonProps={{ danger: true }}
							onConfirm={() => dispatch(deleteBacktestRequest(bt.id))}
						>
							<Button type="text" danger icon={<DeleteOutlined />} />
						</Popconfirm>
					</Tooltip>
				</Space>
			),
		},
	];

	return (
		<div className="p-6">
			<div className="flex items-center justify-end mb-6">
				<Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
					Add
				</Button>
			</div>

			<Table
				rowKey="id"
				columns={columns}
				dataSource={backtests}
				loading={loading}
				pagination={{
					current: page,
					total,
					pageSize: 20,
					showTotal: (t) => `${t} backtests`,
					onChange: (p) => dispatch(fetchBacktestsRequest({ page: p })),
				}}
			/>

			{/* Upsert modal */}
			<UpsertBacktestModal
				open={upsertModalOpen}
				setOpen={setUpsertModalOpen}
				upsertForm={createForm}
				backtest={editingBt}
				setBacktest={setEditingBt}
			/>
		</div>
	);
}
