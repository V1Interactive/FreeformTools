namespace Freeform.Rigging.MocapCleanupDialogue
{
    using Freeform.Core.UI;
    using System;
    using System.Collections.Generic;
    using System.Diagnostics;
    using System.Linq;
    using System.Numerics;
    using System.Text;
    using System.Threading.Tasks;
    using System.Windows.Forms;
    using System.Windows.Media.Media3D;
    using static Freeform.Rigging.AimConstraintDialogue.AimConstraintDialogueVM;

    public class MocapCleanupDialogueVM : ViewModelBase
    {
        public event EventHandler BlendCurvesHandler;
        public event EventHandler OffsetCurvesHandler;
        public event EventHandler ExpandSelectionHandler;
        public event EventHandler FlattenCurvesHandler;
        public event EventHandler FillSelectionHandler;
        public event EventHandler CleanCurvesHandler;

        public RelayCommand BlendCurvesCommand { get; set; }
        public RelayCommand OffsetCurvesCommand { get; set; }
        public RelayCommand ExpandSelectionCommand { get; set; }
        public RelayCommand FlattenCurvesCommand { get; set; }
        public RelayCommand FillSelectionCommand { get; set; }
        public RelayCommand CleanCurvesCommand { get; set; }

        bool _reverseBlend;
        public bool ReverseBlend
        {
            get { return _reverseBlend; }
            set
            {
                if (_reverseBlend != value)
                {
                    _reverseBlend = value;
                    RaisePropertyChanged("ReverseBlend");
                }
            }
        }

        float _threshold;
        public float Threshold
        {
            get { return _threshold; }
            set
            {
                if (_threshold != value)
                {
                    _threshold = value;
                    RaisePropertyChanged("Threshold");
                }
            }
        }

        int _blendFrames;
        public int BlendFrames
        {
            get { return _blendFrames; }
            set
            {
                if (_blendFrames != value)
                {
                    _blendFrames = value;
                    RaisePropertyChanged("BlendFrames");
                }
            }
        }

        public MocapCleanupDialogueVM()
        {
            Threshold = 0.001f;
            BlendFrames = 7;
            ReverseBlend = false;

            BlendCurvesCommand = new RelayCommand(BlendCurvesCall);
            OffsetCurvesCommand = new RelayCommand(OffsetCurvesCall);
            ExpandSelectionCommand = new RelayCommand(ExpandSelectionCall);
            FlattenCurvesCommand = new RelayCommand(FlattenCurvesCall);
            FillSelectionCommand = new RelayCommand(FillSelectionCall);
            CleanCurvesCommand = new RelayCommand(CleanCurvesCall);
        }

        public void BlendCurvesCall(object sender)
        {
            CleanEventArgs eventArgs = new CleanEventArgs()
            {
                Threshold = Threshold,
                MinFrames = BlendFrames,
                Reverse = ReverseBlend,
                Shift = Control.ModifierKeys == Keys.Shift
            };
            BlendCurvesHandler?.Invoke(this, eventArgs);
        }

        public void OffsetCurvesCall(object sender)
        {
            CleanEventArgs eventArgs = new CleanEventArgs()
            {
                Threshold = Threshold,
                MinFrames = BlendFrames,
                Reverse = ReverseBlend,
                Shift = Control.ModifierKeys == Keys.Shift
            };
            OffsetCurvesHandler?.Invoke(this, eventArgs);
        }

        public void ExpandSelectionCall(object sender)
        {
            CleanEventArgs eventArgs = new CleanEventArgs()
            {
                Threshold = Threshold,
                MinFrames = BlendFrames,
                Reverse = ReverseBlend,
                Shift = Control.ModifierKeys == Keys.Shift
            };
            ExpandSelectionHandler?.Invoke(this, eventArgs);
        }

        public void FlattenCurvesCall(object sender)
        {
            CleanEventArgs eventArgs = new CleanEventArgs()
            {
                Threshold = Threshold,
                MinFrames = BlendFrames,
                Reverse = ReverseBlend,
                Shift = Control.ModifierKeys == Keys.Shift
            };
            FlattenCurvesHandler?.Invoke(this, eventArgs);
        }

        public void FillSelectionCall(object sender)
        {
            FillSelectionHandler?.Invoke(this, null);
        }

        public void CleanCurvesCall(object sender)
        {
            CleanEventArgs eventArgs = new CleanEventArgs()
            {
                Threshold = Threshold,
                MinFrames = BlendFrames,
                Reverse = ReverseBlend,
                Shift = Control.ModifierKeys == Keys.Shift
            };
            CleanCurvesHandler?.Invoke(this, eventArgs);
        }

        public class CleanEventArgs : EventArgs
        {
            public float Threshold = 0.001f;
            public int MinFrames = 7;
            public bool Reverse = false;
            public bool Shift = false;
        }
    }
}
