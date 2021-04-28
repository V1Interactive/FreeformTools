namespace Freeform.Rigging.AimConstraintDialogue
{
    using Freeform.Core.UI;
    using System;
    using System.Collections.Generic;
    using System.Linq;
    using System.Numerics;
    using System.Text;
    using System.Threading.Tasks;
    using System.Windows.Media.Media3D;

    public class AimConstraintDialogueVM : ViewModelBase
    {
        public event EventHandler BuildConstraintHandler;

        public RelayCommand BuildConstraintCommand { get; set; }


        int? _startFrame;
        public int? StartFrame
        {
            get { return _startFrame; }
            set
            {
                if (_startFrame != value)
                {
                    _startFrame = value;
                    RaisePropertyChanged("StartFrame");
                }
            }
        }

        int? _endFrame;
        public int? EndFrame
        {
            get { return _endFrame; }
            set
            {
                if (_endFrame != value)
                {
                    _endFrame = value;
                    RaisePropertyChanged("EndFrame");
                }
            }
        }


        public AimConstraintDialogueVM()
        {
            StartFrame = 0;
            EndFrame = 0;

            BuildConstraintCommand = new RelayCommand(BuildConstraintCall);
        }


        public void BuildConstraintCall(object sender)
        {
            Vector3D inputVector = (Vector3D)sender;
            VectorEventArgs eventArgs = new VectorEventArgs()
            {
                Vector = new Vector3((float)inputVector.X, (float)inputVector.Y, (float)inputVector.Z)
            };
            BuildConstraintHandler?.Invoke(this, eventArgs);
        }


        public class VectorEventArgs : EventArgs
        {
            public Vector3 Vector = new Vector3();
        }
    }
}
