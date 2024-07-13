using System;
namespace Freeform.Rigging.ControlColorSet
{
    using System;
    using System.ComponentModel;
    using System.Diagnostics;
    using System.Globalization;
    using System.Windows;
    using System.Windows.Input;
    using System.Windows.Interop;

    using Freeform.Core.UI;

    /// <summary>
    /// Interaction logic for RegionEditor.xaml
    /// </summary>
    public partial class ControlColorSet : Window
    {
        public ControlColorSet()
        {
            InitializeComponent();
            SetupDataContext();
        }

        public ControlColorSet(Process parent)
        {
            InitializeComponent();

            WindowInteropHelper helper = new WindowInteropHelper(this);
            helper.Owner = parent.MainWindowHandle;

            SetupDataContext();
        }

        void SetupDataContext()
        {
            ControlColorSetVM vm = new ControlColorSetVM();
            DataContext = vm;
            if (vm.CloseAction == null)
            {
                vm.CloseAction = new Action(Close);
            }
        }

        protected override void OnClosed(EventArgs e)
        {
            base.OnClosed(e);
            ControlColorSetVM vm = DataContext as ControlColorSetVM;
            vm.Close();
        }

        public void textBox_HexFilterInput(object sender, TextCompositionEventArgs e)
        {
            e.Handled = !int.TryParse(e.Text, NumberStyles.HexNumber, CultureInfo.CurrentCulture, out int hexNumber);
        }
    }
}
