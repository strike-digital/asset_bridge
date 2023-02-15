from .main_thread import update_prop, force_ui_update


class Progress:
    """Used to keep track of the progress of a task, usually downloading an asset."""

    data = None
    propname = ""

    def __init__(self, max, data=None, propname=""):
        self.max = max
        self.data = data or self.data
        self.propname = propname or self.propname
        self.message = ""
        self.cancelled = False
        self.progress = 0
        setattr(self.data, f"{self.propname}_active", True)

    @property
    def progress(self):
        return self._progress

    @progress.setter
    def progress(self, value):
        self._progress = value
        prop_val = self.read()
        if getattr(self.data, self.propname) != prop_val:
            update_prop(self.data, self.propname, prop_val)
            force_ui_update()

    def increment(self, value=1):
        self.progress += value

    def read(self):
        return self.progress / self.max * 100

    def end(self):
        """Reset the progress properties"""
        update_prop(self.data, f"{self.propname}_active", False)
        self._progress = 0
        self.__class__.data = None
        self.__class__.propname = ""

    def cancel(self):
        update_prop(self.data, f"{self.propname}_active", False)
        self.cancelled = True