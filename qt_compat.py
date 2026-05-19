# -*- coding: utf-8 -*-
"""PyQt5 / PyQt6 compatibility helpers."""

from qgis.PyQt.QtCore import Qt


def qgis_action(icon, text, parent):
    try:
        from qgis.PyQt.QtGui import QAction
    except ImportError:
        from qgis.PyQt.QtWidgets import QAction
    return QAction(icon, text, parent)

def qt_user_role():
    if hasattr(Qt, "UserRole"):
        return Qt.UserRole
    return Qt.ItemDataRole.UserRole


def qt_wa_transparent_for_mouse_events():
    """PyQt6: Qt.WidgetAttribute.WA_TransparentForMouseEvents / PyQt5: Qt.WA_TransparentForMouseEvents"""
    wa = getattr(Qt, "WidgetAttribute", None)
    if wa is not None:
        if hasattr(wa, "WA_TransparentForMouseEvents"):
            return wa.WA_TransparentForMouseEvents
        if hasattr(wa, "TransparentForMouseEvents"):
            return wa.TransparentForMouseEvents
    if hasattr(Qt, "WA_TransparentForMouseEvents"):
        return Qt.WA_TransparentForMouseEvents
    return 120  # Qt.WA_TransparentForMouseEvents enum value fallback


def qt_focus_policy_no_focus():
    if hasattr(Qt, "FocusPolicy"):
        return Qt.FocusPolicy.NoFocus
    return Qt.NoFocus


def qt_horizontal_orientation():
    if hasattr(Qt, "Orientation"):
        return Qt.Orientation.Horizontal
    return Qt.Horizontal


def qframe_styled_panel():
    from qgis.PyQt.QtWidgets import QFrame
    shape = getattr(QFrame, "Shape", None)
    if shape is not None and hasattr(shape, "StyledPanel"):
        return shape.StyledPanel
    return QFrame.StyledPanel


def qt_text_selectable_by_mouse():
    if hasattr(Qt, "TextInteractionFlag"):
        return Qt.TextInteractionFlag.TextSelectableByMouse
    return Qt.TextSelectableByMouse


def qt_align_top():
    if hasattr(Qt, "AlignmentFlag"):
        return Qt.AlignmentFlag.AlignTop
    return Qt.AlignTop


def qt_align_center():
    if hasattr(Qt, "AlignmentFlag"):
        return Qt.AlignmentFlag.AlignCenter
    return Qt.AlignCenter


def qt_right_dock_area():
    if hasattr(Qt, "RightDockWidgetArea"):
        return Qt.RightDockWidgetArea
    return Qt.DockWidgetArea.RightDockWidgetArea


def qt_all_dock_widget_areas():
    if hasattr(Qt, "AllDockWidgetAreas"):
        return Qt.AllDockWidgetAreas
    da = getattr(Qt, "DockWidgetArea", None)
    if da is not None:
        return (
            da.LeftDockWidgetArea
            | da.RightDockWidgetArea
            | da.TopDockWidgetArea
            | da.BottomDockWidgetArea
        )
    return (
        Qt.LeftDockWidgetArea
        | Qt.RightDockWidgetArea
        | Qt.TopDockWidgetArea
        | Qt.BottomDockWidgetArea
    )


def qgis_message_level_warning():
    from qgis.core import Qgis
    ml = getattr(Qgis, "MessageLevel", None)
    if ml is not None:
        return ml.Warning
    return Qgis.Warning


def qgis_log_warning(message, tag="주소검색"):
    from qgis.core import QgsMessageLog
    QgsMessageLog.logMessage(message, tag, qgis_message_level_warning())


def line_edit_echo_password():
    from qgis.PyQt.QtWidgets import QLineEdit
    em = getattr(QLineEdit, "EchoMode", None)
    if em is not None and hasattr(em, "Password"):
        return em.Password
    if hasattr(QLineEdit, "Password"):
        return QLineEdit.Password
    return 2


def line_edit_echo_normal():
    from qgis.PyQt.QtWidgets import QLineEdit
    em = getattr(QLineEdit, "EchoMode", None)
    if em is not None and hasattr(em, "Normal"):
        return em.Normal
    if hasattr(QLineEdit, "Normal"):
        return QLineEdit.Normal
    return 0


def qt_scroll_bar_as_needed():
    sp = getattr(Qt, "ScrollBarPolicy", None)
    if sp is not None and hasattr(sp, "ScrollBarAsNeeded"):
        return sp.ScrollBarAsNeeded
    if hasattr(Qt, "ScrollBarAsNeeded"):
        return Qt.ScrollBarAsNeeded
    return 2


def qtext_edit_line_wrap_no_wrap():
    from qgis.PyQt.QtWidgets import QTextEdit
    lwm = getattr(QTextEdit, "LineWrapMode", None)
    if lwm is not None and hasattr(lwm, "NoWrap"):
        return lwm.NoWrap
    if hasattr(QTextEdit, "NoWrap"):
        return QTextEdit.NoWrap
    return 0


def dialog_exec(dlg):
    if hasattr(dlg, "exec"):
        return dlg.exec()
    return dlg.exec_()


def dialog_accepted():
    from qgis.PyQt.QtWidgets import QDialog
    if hasattr(QDialog, "DialogCode"):
        return QDialog.DialogCode.Accepted
    return QDialog.Accepted


def size_policy_fixed_fixed():
    """PyQt5: QSizePolicy.Fixed / PyQt6: QSizePolicy.Policy.Fixed"""
    from qgis.PyQt.QtWidgets import QSizePolicy
    if hasattr(QSizePolicy, "Policy"):
        p = QSizePolicy.Policy
        return QSizePolicy(p.Fixed, p.Fixed)
    return QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)


def qgs_wkb_point_geometry():
    from qgis.core import QgsWkbTypes
    gt = getattr(QgsWkbTypes, "GeometryType", None)
    if gt is not None:
        return gt.PointGeometry
    return QgsWkbTypes.PointGeometry


def qgs_rubberband_icon_cross():
    from qgis.gui import QgsRubberBand
    icon = getattr(QgsRubberBand, "Icon", None)
    if icon is not None and hasattr(icon, "ICON_CROSS"):
        return icon.ICON_CROSS
    return QgsRubberBand.ICON_CROSS


def transform_wgs84_to_map_point(iface, longitude, latitude):
    """Kakao x,y (WGS84) -> map canvas CRS."""
    from qgis.core import (
        QgsCoordinateReferenceSystem,
        QgsCoordinateTransform,
        QgsProject,
        QgsPointXY,
    )

    ctx = QgsProject.instance().transformContext()
    src = QgsCoordinateReferenceSystem("EPSG:4326")
    dest = iface.mapCanvas().mapSettings().destinationCrs()
    if not dest.isValid():
        raise ValueError("맵 CRS가 설정되지 않았습니다.")

    tr = QgsCoordinateTransform(src, dest, ctx)
    pt = QgsPointXY(float(longitude), float(latitude))

    direction = getattr(QgsCoordinateTransform, "TransformDirection", None)
    if direction is not None and hasattr(direction, "ForwardTransform"):
        return tr.transform(pt, direction.ForwardTransform)
    if hasattr(QgsCoordinateTransform, "ForwardTransform"):
        return tr.transform(pt, QgsCoordinateTransform.ForwardTransform)
    return tr.transform(pt)
