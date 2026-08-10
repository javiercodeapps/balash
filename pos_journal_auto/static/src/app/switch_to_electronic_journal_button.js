import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { ask, makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { SelectionPopup } from "@point_of_sale/app/components/popups/selection_popup/selection_popup";

export class SwitchToElectronicJournalButton extends Component {
    static template = "pos_journal_auto.SwitchToElectronicJournalButton";
    static props = { order: Object };

    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.lock = false;
    }

    get isVisible() {
        const order = this.props.order;
        return Boolean(
            order?.raw?.account_move && order?.raw?.invoice_can_switch_to_electronic_journal
        );
    }

    get label() {
        return _t("Change to Electronic");
    }

    async click() {
        if (this.lock) {
            return;
        }

        const order = this.props.order;
        if (!order) {
            return;
        }

        this.lock = true;
        try {
            const journals = await this.pos.data.call(
                "pos.order",
                "action_pos_journal_auto_get_electronic_journals",
                [order.id]
            );
            if (!journals.length) {
                this.env.services.notification.add(_t("No electronic journal is available."), {
                    type: "warning",
                });
                return;
            }

            const journalId = await makeAwaitable(this.dialog, SelectionPopup, {
                title: _t("Electronic Journal"),
                list: journals.map(([id, name]) => ({ id, label: name, item: id })),
            });
            if (!journalId) {
                return;
            }

            const confirmed = await ask(this.dialog, {
                title: _t("Confirm switch to electronic journal"),
                body: _t(
                    "The current invoice will be voided and a new one will be created in the selected electronic journal. Continue?"
                ),
                confirmLabel: _t("Switch"),
                confirmClass: "btn-danger",
            });
            if (!confirmed) {
                return;
            }

            const result = await this.pos.data.call(
                "pos.order",
                "action_pos_journal_auto_switch_invoice",
                [order.id, journalId]
            );

            await this.pos.data.loadServerOrders([["id", "=", order.id]]);
            this.env.services.notification.add(
                _t("Invoice %s re-issued as %s.", result.old_invoice_name, result.new_invoice_name),
                { type: "success" }
            );
        } finally {
            this.lock = false;
        }
    }
}
