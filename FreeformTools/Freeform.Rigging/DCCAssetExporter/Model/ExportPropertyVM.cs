using Freeform.Core.UI;
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using static Freeform.Rigging.DCCAssetExporter.DCCAssetExporterVM;

namespace Freeform.Rigging.DCCAssetExporter
{
    public class ExportPropertyVM : INotifyPropertyChanged
    {
        public event EventHandler PropertyHandler;

        public RelayCommand PropertyCommand { get; set; }


        private string _propertyName;
        public string PropertyName
        {
            get { return _propertyName; }
            set
            {
                if (_propertyName != value)
                {
                    _propertyName = value;
                    RaisePropertyChanged("PropertyName");
                }
            }
        }

        private string _displayName;
        public string DisplayName
        {
            get { return _displayName; }
            set
            {
                if (_displayName != value)
                {
                    _displayName = value;
                    RaisePropertyChanged("DisplayName");
                }
            }
        }

        public string ParentProcessName { get; set; }

        public bool MaxDisabled
        {
            get { return ParentProcessName != "3dsMax"; }
        }

        public bool MaxEnabled
        {
            get { return ParentProcessName == "3dsMax"; }
        }

        public ExportPropertyVM(string propertyName, string uiName, string parentProcessName)
        {
            PropertyName = propertyName;
            DisplayName = uiName;
            ParentProcessName = parentProcessName;

            PropertyCommand = new RelayCommand(PropertyCall);
        }

        public void PropertyCall(object sender)
        {
            var exportObject = sender as ExportObject;
            CreateProperty(exportObject);
        }

        public void CreateProperty(ExportObject exportObject)
        {
            ExportPropertyEventArgs eventArgs = new ExportPropertyEventArgs()
            {
                ExportPropertyName = PropertyName,
                NodeName = exportObject.NodeName
            };

            PropertyHandler?.Invoke(this, eventArgs);

            if (eventArgs.Object != null)
            {
                exportObject.AddExportProperty(eventArgs.Object);
            }
        }

        public class ExportPropertyEventArgs : EventArgs
        {
            public string ExportPropertyName = string.Empty;
            public string NodeName = string.Empty;
            public ExportProperty Object = null;
        }

        protected void RaisePropertyChanged(string prop)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(prop));
        }
        public event PropertyChangedEventHandler PropertyChanged;
    }
}
