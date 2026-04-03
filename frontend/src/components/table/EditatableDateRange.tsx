import { useState } from "react";
import { Button, DatePicker } from "antd";
import dayjs from "dayjs";
import type { Dayjs } from "dayjs";
import { EditOutlined } from "@ant-design/icons";

const EditableDateRange = ({
	start,
	end,
	onSave,
}: {
	start: string;
	end: string;
	onSave: (start: string, end: string) => void;
}) => {
	const [editing, setEditing] = useState(false);

	const startEdit = (e: React.MouseEvent) => {
		e.stopPropagation();
		setEditing(true);
	};

	if (editing) {
		return (
			<DatePicker.RangePicker
				picker="month"
				size="small"
				format="YYYY-MM"
				defaultValue={[dayjs(start), dayjs(end)] as [Dayjs, Dayjs]}
				autoFocus
				open
				onChange={(dates, strs) => {
					if (dates && strs[0] && strs[1])
						onSave(strs[0] + "-01", strs[1] + "-01");
					setEditing(false);
				}}
				onOpenChange={(open) => {
					if (!open) setEditing(false);
				}}
				onClick={(e) => e.stopPropagation()}
			/>
		);
	}

	return (
		<div className="flex items-center justify-between gap-2">
			<span className="text-sm">
				{start.slice(0, 7)} → {end.slice(0, 7)}
			</span>
			<Button
				type="text"
				size="small"
				icon={<EditOutlined />}
				onClick={startEdit}
				className="shrink-0"
			/>
		</div>
	);
};

export default EditableDateRange;
